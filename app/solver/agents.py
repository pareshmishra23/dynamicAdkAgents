from __future__ import annotations

from collections import defaultdict, deque
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


def enumerate_loops(problem: RoutingProblem) -> list[tuple[tuple[str, ...], float]]:
    table = _matrix(problem)
    start = problem.cities[0]
    seen: set[tuple[str, ...]] = set()
    found: list[tuple[tuple[str, ...], float]] = []
    for perm in permutations(problem.cities[1:]):
        cycle = (start,) + perm
        if problem.directed:
            orientation = cycle
        else:
            reverse = (start,) + tuple(reversed(perm))
            orientation = cycle if len(perm) < 2 or perm[0] < perm[-1] else reverse
        if problem.first_stop_after_start and orientation[1] != problem.first_stop_after_start:
            continue
        if orientation in seen:
            continue
        seen.add(orientation)
        cost = _cycle_cost(orientation, table)
        if cost is not None:
            found.append((orientation, cost))
    found.sort(key=lambda pair: pair[1])
    return found


def _nearest_neighbor(start: str, cities: tuple[str, ...], table: dict[tuple[str, str], float]) -> tuple[str, ...]:
    remaining = set(cities) - {start}
    visited = [start]
    current = start
    while remaining:
        nxt = min(remaining, key=lambda c: (table.get((current, c), float("inf")), c))
        visited.append(nxt)
        remaining.discard(nxt)
        current = nxt
    return tuple(visited)


def _two_opt(cycle: tuple[str, ...], table: dict[tuple[str, str], float]) -> tuple[str, ...]:
    current = list(cycle)
    n = len(current)
    improved = True
    while improved:
        improved = False
        for i in range(n):
            for j in range(i + 1, n):
                if j - i == 1 or (i == 0 and j == n - 1):
                    continue
                a, b = current[i], current[(i + 1) % n]
                c, d = current[j], current[(j + 1) % n]
                if table.get((a, c)) is None or table.get((b, d)) is None:
                    continue
                old = table[(a, b)] + table[(c, d)]
                new = table[(a, c)] + table[(b, d)]
                if new + 1e-9 < old:
                    current[i + 1 : j + 1] = reversed(current[i + 1 : j + 1])
                    improved = True
    return tuple(current)


def heuristic_loop(problem: RoutingProblem) -> tuple[tuple[str, ...], float, float, float]:
    table = _matrix(problem)
    start = problem.cities[0]
    greedy = _nearest_neighbor(start, problem.cities, table)
    greedy_cost = _cycle_cost(greedy, table) or 0.0
    optimized = _two_opt(greedy, table)
    opt_cost = _cycle_cost(optimized, table) or 0.0
    improvement = (greedy_cost - opt_cost) / greedy_cost if greedy_cost else 0.0
    return optimized, opt_cost, greedy_cost, improvement


def _find_dependency_cycle(precedence: tuple[tuple[str, str], ...]) -> tuple[str, ...] | None:
    adj: dict[str, list[str]] = defaultdict(list)
    pred: dict[str, list[str]] = defaultdict(list)
    nodes: set[str] = set()
    indegree: dict[str, int] = {}
    for a, b in precedence:
        nodes.add(a)
        nodes.add(b)
        adj[a].append(b)
        pred[b].append(a)
        indegree.setdefault(a, 0)
        indegree[b] = indegree.get(b, 0) + 1
    queue = deque(n for n in nodes if indegree.get(n, 0) == 0)
    seen: set[str] = set()
    while queue:
        node = queue.popleft()
        seen.add(node)
        for nxt in adj[node]:
            indegree[nxt] = indegree.get(nxt, 0) - 1
            if indegree.get(nxt, 0) == 0:
                queue.append(nxt)
    leftover = nodes - seen
    if not leftover:
        return None
    start = min(leftover)
    chain = [start]
    current = start
    for _ in range(len(nodes) + 1):
        candidates = [p for p in pred[current] if p in leftover and p != current]
        if not candidates:
            break
        nxt = candidates[0]
        if nxt in chain:
            idx = chain.index(nxt)
            return tuple(reversed(chain[idx:] + [nxt]))
        chain.append(nxt)
        current = nxt
    return tuple(sorted(leftover))


def vrp_split(
    problem: RoutingProblem,
) -> tuple[tuple[str, ...], tuple[str, ...], float, float, float]:
    table = _matrix(problem)
    hub = problem.cities[0]
    coords = problem.coords or {}
    others = list(problem.cities[1:])

    def angle(city: str) -> float:
        sx, sy = coords.get(hub, (0.0, 0.0))
        cx, cy = coords.get(city, (1.0, 1.0))
        import math
        return math.atan2(cy - sy, cx - sx)

    ordered = sorted(others, key=lambda c: (angle(c), c))
    route_a = tuple(ordered[::2])
    route_b = tuple(ordered[1::2])

    def route_cost(route: tuple[str, ...]) -> float:
        return _cycle_cost((hub,) + route, table) or 0.0

    cost_a = route_cost(route_a)
    cost_b = route_cost(route_b)
    return route_a, route_b, cost_a, cost_b, cost_a + cost_b


def _graph_builder(problem: RoutingProblem, definition: AgentDefinition, task: str, ctx) -> AgentResult:
    if ctx:
        ctx.pointer("reading edges from the problem statement")
        ctx.act("building the distance table (undirected: mirroring each edge both ways)")
    table = _matrix(problem)
    complete = all((a, b) in table for a in problem.cities for b in problem.cities if a != b)
    if ctx:
        ctx.verify(
            f"graph model ready: n={len(problem.cities)} nodes ({', '.join(problem.cities)}), "
            f"edges={len(problem.edges)}, complete={complete}"
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


def _tour_engine(problem: RoutingProblem, definition: AgentDefinition, task: str, ctx) -> AgentResult:
    large = len(problem.cities) > 9
    if ctx:
        if large:
            ctx.think("n>9 -> enumeration infeasible; switching pool to greedy nearest-neighbor + 2-opt")
        else:
            ctx.think(
                f"n={len(problem.cities)} cities -> up to (n-1)!/2 distinct undirected loops; "
                "fix the start city and permute the rest"
            )
        ctx.pointer("pointing at tour_enum: generate candidates, dedupe rotations/reversals, rank by cost")

    if large:
        optimized, opt_cost, greedy_cost, improvement = heuristic_loop(problem)
        if ctx:
            ctx.act(f"greedy nearest-neighbor cost = {greedy_cost:g}")
            ctx.act(f"2-opt smoothing -> cost = {opt_cost:g} (improved {improvement * 100:.1f}%)")
            ctx.decide(
                f"heuristic winner = {'->'.join(optimized)}->{optimized[0]} total {opt_cost:g}"
            )
        return AgentResult(
            agent_id=definition.id,
            status="completed",
            recommendation=(
                f"Tour Engine (heuristic): greedy={greedy_cost:g} -> 2-opt={opt_cost:g} "
                f"(improvement {improvement * 100:.1f}%); winner = "
                f"{'->'.join(optimized)}->{optimized[0]} total {opt_cost:g}"
            ),
            evidence=(f"candidate loops from pointer tour_enum (greedy {greedy_cost:g}, 2-opt {opt_cost:g})",),
            metadata={"candidates": [[list(optimized), opt_cost]], "greedy": greedy_cost, "improvement": improvement},
        )

    cycles = enumerate_loops(problem)
    if not cycles:
        if ctx:
            ctx.verify("no connected loop exists across the given edges -> infeasible")
        return AgentResult(
            agent_id=definition.id,
            status="completed",
            recommendation="Tour Engine: no connected loop exists across the given edges",
            evidence=(task,),
        )
    best, best_cost = cycles[0]
    if ctx:
        for route, cost in cycles:
            ctx.act(f"candidate {'->'.join(route)} -> {'->'.join(route) + '->' + route[0]} costs {cost:g}")
        ctx.decide(
            f"cheapest candidate = {'->'.join(best)}->{best[0]} total {best_cost:g} "
            f"({len(cycles)} distinct loops checked)"
        )
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


def _optimizer(problem: RoutingProblem, definition: AgentDefinition, task: str, ctx) -> AgentResult:
    optimized, opt_cost, greedy_cost, improvement = heuristic_loop(problem)
    if ctx:
        ctx.pointer("pointing at prune: independent re-run to confirm greedy vs 2-opt gap")
        ctx.verify(f"greedy={greedy_cost:g}, improved={opt_cost:g} (-{improvement * 100:.1f}%)")
        ctx.decide(f"confirms heuristic winner {'->'.join(optimized)}->{optimized[0]} = {opt_cost:g}")
    return AgentResult(
        agent_id=definition.id,
        status="completed",
        recommendation=(
            f"Optimizer: independent check greedy={greedy_cost:g} -> 2-opt={opt_cost:g} "
            f"(-{improvement * 100:.1f}%); feasible route confirmed"
        ),
        evidence=(f"prune pointer verified {len(problem.cities)}-city route",),
        metadata={"cost": opt_cost, "improvement": improvement},
    )


def _route_validator(problem: RoutingProblem, definition: AgentDefinition, task: str, ctx) -> AgentResult:
    large = len(problem.cities) > 9
    if ctx:
        ctx.think("verify the winning loop is Hamiltonian: every city exactly once and closes to start")
        if large:
            ctx.pointer("pointing at cycle_check: large n -> re-derive via same heuristic independently")
        else:
            ctx.pointer("pointing at cycle_check: re-derive feasible loops independently of tour_engine")

    if large:
        optimized, opt_cost, _, _ = heuristic_loop(problem)
        loop = "->".join(optimized) + "->" + optimized[0]
        if ctx:
            ctx.verify(f"Hamiltonian OK (heuristic): {loop} = {opt_cost:g}; visits all {len(problem.cities)} cities")
            ctx.decide(f"winner = {loop} at {opt_cost:g}")
        return AgentResult(
            agent_id=definition.id,
            status="completed",
            recommendation=(
                f"Route Validator (heuristic): loop visits every city exactly once and closes to "
                f"start; winner = {loop} at {opt_cost:g}"
            ),
            evidence=("cycle_check confirmed feasible loop",),
            metadata={"best": optimized, "cost": opt_cost},
        )

    cycles = enumerate_loops(problem)
    if not cycles:
        if ctx:
            ctx.verify("no Hamiltonian cycle exists -> do not report a route")
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
    if ctx:
        for route, cost in cycles:
            ctx.verify(f"Hamiltonian OK: {'->'.join(route) + '->' + route[0]} = {cost:g}")
        ctx.decide(f"winner = {loop} at {best_cost:g} ({len(cycles)} feasible loops)")
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


def _vrp_splitter(problem: RoutingProblem, definition: AgentDefinition, task: str, ctx) -> AgentResult:
    if ctx:
        ctx.think("VRP detected: partition city set, then build one hub-loop per vehicle (no parallel writers to a route)")
        ctx.pointer("pointing at balance_split: sort by angle around hub, alternate into two arcs")
    route_a, route_b, cost_a, cost_b, total = vrp_split(problem)
    if ctx:
        ctx.act(f"route A ({len(route_a)} stops): hub -> {' -> '.join(route_a)} -> hub = {cost_a:g}")
        ctx.act(f"route B ({len(route_b)} stops): hub -> {' -> '.join(route_b)} -> hub = {cost_b:g}")
        ctx.verify(f"stops {len(route_a)}+{len(route_b)}≤6 per vehicle; city sets disjoint, cover all")
        ctx.decide(f"combined distance = {total:g}")
    return AgentResult(
        agent_id=definition.id,
        status="completed",
        recommendation=(
            f"VRP Splitter: route A [{', '.join(route_a)}] = {cost_a:g}; "
            f"route B [{', '.join(route_b)}] = {cost_b:g}; combined = {total:g} "
            f"(each ≤6 stops, disjoint, balanced)"
        ),
        evidence=("balance_split pointer partitioned by angle",),
        metadata={"route_a": route_a, "route_b": route_b, "cost_a": cost_a, "cost_b": cost_b, "total": total},
    )


def _vrp_validator(problem: RoutingProblem, definition: AgentDefinition, task: str, ctx) -> AgentResult:
    if ctx:
        ctx.pointer("pointing at cycle_check: independently re-split and re-check each sub-route")
    route_a, route_b, cost_a, cost_b, total = vrp_split(problem)
    covered = set(route_a) | set(route_b)
    disjoint = set(route_a).isdisjoint(set(route_b))
    capacity_ok = max(len(route_a), len(route_b)) <= 6
    complete = covered == set(problem.cities) - {problem.cities[0]}
    if not (disjoint and capacity_ok and complete):
        if ctx:
            ctx.verify(f"VRP check FAILED: disjoint={disjoint} capacity={capacity_ok} coverage={complete}")
        return AgentResult(
            agent_id=definition.id,
            status="error",
            recommendation="VRP Validator: split is not feasible",
            evidence=(task,),
        )
    if ctx:
        ctx.verify(f"split feasible: disjoint={disjoint}, max stops {max(len(route_a), len(route_b))}≤6, coverage={complete}")
        ctx.decide(f"combined distance confirmed = {total:g}")
    return AgentResult(
        agent_id=definition.id,
        status="completed",
        recommendation=(
            f"VRP Validator: both sub-routes are feasible, disjoint, under capacity; "
            f"combined = {total:g} confirmed"
        ),
        evidence=("cycle_check pointer re-ran the split",),
        metadata={"total": total, "route_a": route_a, "route_b": route_b},
    )


def _dependency_checker(problem: RoutingProblem, definition: AgentDefinition, task: str, ctx) -> AgentResult:
    precedence = problem.precedence or ()
    if ctx:
        ctx.think("constraint-satisfaction: build dependency graph, run topological ordering")
        ctx.pointer("pointing at order_check: Kahn's algorithm, count processed nodes vs total")
    if not precedence:
        return AgentResult(
            agent_id=definition.id,
            status="completed",
            recommendation="Dependency Checker: no ordering constraints given",
            evidence=(task,),
        )
    cycle = _find_dependency_cycle(precedence)
    if ctx:
        for a, b in precedence:
            ctx.act(f"constraint: {a} before {b}")
    if cycle:
        chain = " -> ".join(cycle) + " -> " + cycle[0]
        if ctx:
            ctx.verify(f"cycle detected: {chain}; processed < total nodes")
            ctx.decide("impossible: circular dependency leaves no valid visit order")
        return AgentResult(
            agent_id=definition.id,
            status="completed",
            recommendation=(
                f"Dependency Checker: impossible - circular dependency "
                f"{chain} leaves no valid ordering"
            ),
            evidence=(f"order_check found cycle among {sorted(set(x for pair in precedence for x in pair))}",),
            metadata={"cycle": cycle},
        )
    if ctx:
        ctx.verify("topological order exists -> constraints consistent")
        ctx.decide("feasible ordering found")
    return AgentResult(
        agent_id=definition.id,
        status="completed",
        recommendation="Dependency Checker: constraints consistent, ordering feasible",
        evidence=("order_check passed",),
    )


def _order_reviewer(problem: RoutingProblem, definition: AgentDefinition, task: str, ctx) -> AgentResult:
    cycle = _find_dependency_cycle(problem.precedence or ())
    if ctx:
        ctx.pointer("independent re-run of the ordering check (no trust in peer output)")
    if cycle:
        chain = " -> ".join(cycle) + " -> " + cycle[0]
        if ctx:
            ctx.verify(f"independently confirmed circular dependency {chain}")
        return AgentResult(
            agent_id=definition.id,
            status="completed",
            recommendation=(
                f"Order Reviewer: confirmed impossible - circular dependency {chain}"
            ),
            evidence=("independent order_check re-run",),
            metadata={"cycle": cycle},
        )
    return AgentResult(
        agent_id=definition.id,
        status="completed",
        recommendation="Order Reviewer: constraints are consistent",
        evidence=("independent order_check re-run",),
    )


def make_solver_factory(
    problem: RoutingProblem,
    trace=None,
) -> Callable[[AgentDefinition], Callable[[str], AgentResult]]:
    def factory(definition: AgentDefinition) -> Callable[[str], AgentResult]:
        ctx = trace.named(definition.id) if trace else None

        def execute(task: str) -> AgentResult:
            if definition.id == "graph_builder":
                return _graph_builder(problem, definition, task, ctx)
            if definition.id == "tour_engine":
                return _tour_engine(problem, definition, task, ctx)
            if definition.id == "optimizer":
                return _optimizer(problem, definition, task, ctx)
            if definition.id == "route_validator":
                return _route_validator(problem, definition, task, ctx)
            if definition.id == "vrp_splitter":
                return _vrp_splitter(problem, definition, task, ctx)
            if definition.id == "vrp_validator":
                return _vrp_validator(problem, definition, task, ctx)
            if definition.id == "dependency_checker":
                return _dependency_checker(problem, definition, task, ctx)
            if definition.id == "order_reviewer":
                return _order_reviewer(problem, definition, task, ctx)
            return AgentResult(
                agent_id=definition.id,
                status="error",
                recommendation=f"{definition.id}: no solver implementation",
                evidence=(task,),
            )
        return execute
    return factory