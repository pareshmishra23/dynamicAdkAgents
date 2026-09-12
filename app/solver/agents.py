from __future__ import annotations

from itertools import permutations
from typing import Callable

from app.models import AgentDefinition, AgentResult
from app.solver.problems import RoutingProblem


def _matrix(problem: RoutingProblem) -> dict[tuple[str, str], float]:
    table: dict[tuple[str, str], float] = {}
    for edge in problem.edges:
        table[(edge.a, edge.b)] = edge.cost
        if not problem.directed:
            table[(edge.b, edge.a)] = edge.cost
    return table


def _cycle_cost(cycle: tuple[str, ...], table: dict[tuple[str, str], float]) -> float | None:
    total = 0.0
    for a, b in zip(cycle, cycle[1:] + (cycle[0],)):
        cost = table.get((a, b))
        if cost is None:
            return None
        total += cost
    return total


def _distinct_cycles(problem: RoutingProblem) -> list[tuple[tuple[str, ...], float]]:
    cities = problem.cities
    table = _matrix(problem)
    start = cities[0]
    seen: set[tuple[str, ...]] = set()
    found: list[tuple[tuple[str, ...], float]] = []
    for perm in permutations(cities[1:]):
        cycle = (start,) + perm
        reverse = (start,) + tuple(reversed(perm))
        orientation = cycle if len(perm) < 2 or perm[0] < perm[-1] else reverse
        if orientation in seen:
            continue
        seen.add(orientation)
        cost = _cycle_cost(orientation, table)
        if cost is not None:
            found.append((orientation, cost))
    found.sort(key=lambda pair: pair[1])
    return found


def _graph_builder(problem: RoutingProblem, definition: AgentDefinition, task: str) -> AgentResult:
    table = _matrix(problem)
    complete = all(
        (a, b) in table for a in problem.cities for b in problem.cities if a != b
    )
    return AgentResult(
        agent_id=definition.id,
        status="completed",
        recommendation=(
            f"Graph built: n={len(problem.cities)} nodes ({', '.join(problem.cities)}), "
            f"edges=[{' '.join(e.a + e.b + '=' + str(e.cost) for e in problem.edges)}], "
            f"complete={complete}, directed={problem.directed}"
        ),
        evidence=("distance matrix derived from problem edges for pointer matrix_build",),
        metadata={"edges": [(e.a, e.b, e.cost) for e in problem.edges]},
    )


def _tour_engine(problem: RoutingProblem, definition: AgentDefinition, task: str) -> AgentResult:
    cycles = _distinct_cycles(problem)
    if not cycles:
        return AgentResult(
            agent_id=definition.id,
            status="completed",
            recommendation="Tour Engine: no connected loop exists across the given edges",
            evidence=(task,),
        )
    best, best_cost = cycles[0]
    summary = "; ".join(f"{'->'.join(c)}={cost:g}" for c, cost in cycles)
    return AgentResult(
        agent_id=definition.id,
        status="completed",
        recommendation=(
            f"Tour Engine: enumerated {len(cycles)} distinct loops [{summary or 'none'}]; "
            f"cheapest candidate = {'->'.join(best)} -> {best[0]} total {best_cost:g}"
        ),
        evidence=(f"candidate loops from pointer tour_enum: {summary}",),
        metadata={"candidates": [[c, cost] for c, cost in cycles]},
    )


def _route_validator(problem: RoutingProblem, definition: AgentDefinition, task: str) -> AgentResult:
    cycles = _distinct_cycles(problem)
    if not cycles:
        return AgentResult(
            agent_id=definition.id,
            status="completed",
            recommendation=(
                "Route Validator: impossible - no Hamiltonian cycle exists "
                "(graph disconnected or constraint contradiction); do not report a route"
            ),
            evidence=(f"feasibility from pointer cycle_check from {task}",),
        )
    best, best_cost = cycles[0]
    loop = "->".join(best) + "->" + best[0]
    return AgentResult(
        agent_id=definition.id,
        status="completed",
        recommendation=(
            f"Route Validator: {len(cycles)} valid Hamiltonian loop(s), each visiting every "
            f"city exactly once and closing to start; winner = {loop} at {best_cost:g}"
        ),
        evidence=(f"cycle_check confirmed {len(cycles)} feasible loop(s)",),
        metadata={"best": best, "cost": best_cost, "loops": cycles},
    )


def make_solver_factory(problem: RoutingProblem) -> Callable[[AgentDefinition], Callable[[str], AgentResult]]:
    def factory(definition: AgentDefinition) -> Callable[[str], AgentResult]:
        def execute(task: str) -> AgentResult:
            if definition.id == "graph_builder":
                return _graph_builder(problem, definition, task)
            if definition.id == "tour_engine":
                return _tour_engine(problem, definition, task)
            if definition.id == "route_validator":
                return _route_validator(problem, definition, task)
            return AgentResult(
                agent_id=definition.id,
                status="error",
                recommendation=f"{definition.id}: no solver implementation",
                evidence=(task,),
            )
        return execute
    return factory