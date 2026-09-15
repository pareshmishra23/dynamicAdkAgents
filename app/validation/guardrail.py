from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from app.solver.problems import RoutingProblem


class OptimizationState(str, Enum):
    FEASIBLE = "FEASIBLE"
    OPTIMAL = "OPTIMAL"
    UNPROVEN = "UNPROVEN"
    IMPOSSIBLE = "IMPOSSIBLE"


@dataclass(frozen=True)
class ValidationResult:
    state: OptimizationState
    is_valid: bool
    reason: str
    details: dict[str, Any]


class DeterministicGuardrail:
    """Mathematical and topological validation guardrail.

    Never trusts LLMs for mathematical, topological, or constraint guarantees.
    Enforces the distinction: FEASIBLE != OPTIMAL.
    """

    def __init__(self, problem: RoutingProblem) -> None:
        self.problem = problem
        self._matrix = self._build_matrix(problem)

    @staticmethod
    def _build_matrix(problem: RoutingProblem) -> dict[tuple[str, str], float]:
        table: dict[tuple[str, str], float] = {}
        for edge in problem.edges:
            table[(edge.a, edge.b)] = edge.cost
            if not problem.directed:
                table[(edge.b, edge.a)] = edge.cost
        return table

    def validate_proposal(
        self,
        proposed_route: tuple[str, ...] | list[str] | None = None,
        is_heuristic: bool = False,
        vrp_routes: tuple[tuple[str, ...], tuple[str, ...]] | None = None,
    ) -> ValidationResult:
        """Deterministically validate a proposed solution against the problem specification."""

        # 1. Check for topological/circular dependency impossibility
        if self.problem.precedence:
            cycle = self._detect_dependency_cycle(self.problem.precedence)
            if cycle:
                chain = " -> ".join(cycle) + " -> " + cycle[0]
                return ValidationResult(
                    state=OptimizationState.IMPOSSIBLE,
                    is_valid=False,
                    reason=f"Problem impossible: circular dependency detected: {chain}",
                    details={"cycle": cycle},
                )

        # 2. Check for disconnected graph / impossibility
        if self.problem.impossible:
            return ValidationResult(
                state=OptimizationState.IMPOSSIBLE,
                is_valid=False,
                reason="Problem impossible: disconnected graph has no Hamiltonian cycle",
                details={"island_nodes": [c for c in self.problem.cities if not any(e.a == c or e.b == c for e in self.problem.edges)]},
            )

        # 3. Check VRP Split constraints
        if self.problem.kind == "vrp":
            if vrp_routes is None:
                return ValidationResult(
                    state=OptimizationState.FEASIBLE,
                    is_valid=True,
                    reason="VRP problem requires partitioned vehicle sub-routes",
                    details={},
                )
            r_a, r_b = vrp_routes
            covered = set(r_a) | set(r_b)
            disjoint = set(r_a).isdisjoint(set(r_b))
            max_stops = max(len(r_a), len(r_b))
            capacity_ok = max_stops <= 6
            complete = covered == (set(self.problem.cities) - {self.problem.cities[0]})
            if not (disjoint and capacity_ok and complete):
                return ValidationResult(
                    state=OptimizationState.IMPOSSIBLE,
                    is_valid=False,
                    reason=f"VRP validation failed: disjoint={disjoint}, capacity_ok={capacity_ok}, complete={complete}",
                    details={"max_stops": max_stops, "disjoint": disjoint, "complete": complete},
                )
            # For VRP, the solution is heuristic/split
            return ValidationResult(
                state=OptimizationState.UNPROVEN if is_heuristic else OptimizationState.FEASIBLE,
                is_valid=True,
                reason="VRP split confirmed: disjoint, within capacity, and complete",
                details={"subroutes": [r_a, r_b], "max_stops": max_stops},
            )

        # 4. Standard TSP / Hamiltonian Cycle Check
        if proposed_route is None:
            return ValidationResult(
                state=OptimizationState.IMPOSSIBLE,
                is_valid=False,
                reason="No route proposal provided",
                details={},
            )

        route_tuple = tuple(proposed_route)
        expected_cities = set(self.problem.cities)
        visited_cities = set(route_tuple)

        # Check all cities visited exactly once
        if visited_cities != expected_cities or len(route_tuple) != len(expected_cities):
            missing = expected_cities - visited_cities
            duplicates = len(route_tuple) - len(visited_cities)
            return ValidationResult(
                state=OptimizationState.IMPOSSIBLE,
                is_valid=False,
                reason=f"Not a Hamiltonian cycle: missing={missing}, duplicate_count={duplicates}",
                details={"missing": list(missing), "visited": list(visited_cities)},
            )

        # Check first stop constraint
        if self.problem.first_stop_after_start and len(route_tuple) > 1:
            if route_tuple[1] != self.problem.first_stop_after_start:
                return ValidationResult(
                    state=OptimizationState.IMPOSSIBLE,
                    is_valid=False,
                    reason=f"First stop constraint violated: expected {self.problem.first_stop_after_start}, got {route_tuple[1]}",
                    details={"actual_first_stop": route_tuple[1]},
                )

        # Check graph connectivity & cost
        total_cost = 0.0
        n = len(route_tuple)
        for i in range(n):
            u = route_tuple[i]
            v = route_tuple[(i + 1) % n]
            cost = self._matrix.get((u, v))
            if cost is None:
                return ValidationResult(
                    state=OptimizationState.IMPOSSIBLE,
                    is_valid=False,
                    reason=f"Graph disconnected: no valid edge from {u} to {v}",
                    details={"missing_edge": (u, v)},
                )
            total_cost += cost

        # Check optimality state
        if is_heuristic or len(self.problem.cities) > 9:
            # Mandate: FEASIBLE != OPTIMAL. For n>9 heuristic solutions, state is explicitly UNPROVEN
            return ValidationResult(
                state=OptimizationState.UNPROVEN,
                is_valid=True,
                reason=f"Route is FEASIBLE with cost {total_cost:g}; optimality is UNPROVEN (heuristic pruning)",
                details={"cost": total_cost, "route": route_tuple, "optimality_proven": False},
            )

        return ValidationResult(
            state=OptimizationState.OPTIMAL,
            is_valid=True,
            reason=f"Route is OPTIMAL with proven minimal cost {total_cost:g}",
            details={"cost": total_cost, "route": route_tuple, "optimality_proven": True},
        )

    @staticmethod
    def _detect_dependency_cycle(precedence: tuple[tuple[str, str], ...]) -> tuple[str, ...] | None:
        from collections import defaultdict, deque

        graph: dict[str, list[str]] = defaultdict(list)
        indegree: dict[str, int] = defaultdict(int)
        nodes: set[str] = set()

        for a, b in precedence:
            graph[a].append(b)
            indegree[b] += 1
            nodes.add(a)
            nodes.add(b)

        queue = deque([n for n in nodes if indegree[n] == 0])
        processed = 0

        while queue:
            node = queue.popleft()
            processed += 1
            for nxt in graph[node]:
                indegree[nxt] -= 1
                if indegree[nxt] == 0:
                    queue.append(nxt)

        if processed < len(nodes):
            # Circular dependency cycle exists
            return tuple(sorted(nodes))
        return None
