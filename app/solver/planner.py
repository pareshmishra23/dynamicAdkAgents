from __future__ import annotations

from dataclasses import dataclass

from app.models import AgentDefinition, AgentLimits
from app.solver.problems import RoutingProblem


@dataclass(frozen=True)
class PlannedAgent:
    definition: AgentDefinition
    reason: str
    task: str


@dataclass(frozen=True)
class AgentPlan:
    problem: RoutingProblem
    agents: tuple[PlannedAgent, ...]
    rationale: str


def _spawn(agent_id: str, name: str, capability: str, tool: str, reason: str, task: str) -> PlannedAgent:
    return PlannedAgent(
        definition=AgentDefinition(
            id=agent_id,
            version="1.0",
            enabled=True,
            name=name,
            description=f"{name} for {capability}",
            capabilities=(capability,),
            instructions=f"You are the {name}.",
            input_contract={},
            output_contract={"type": "object", "required": ["answer"]},
            allowed_tools=(tool,),
            limits=AgentLimits(),
        ),
        reason=reason,
        task=task,
    )


def _graph_builder(problem: RoutingProblem) -> PlannedAgent:
    return _spawn(
        "graph_builder", "Graph Builder", "graph", "matrix_build",
        "base specialist: every routing problem needs a distance model to point at",
        f"build the distance graph for {problem.title}",
    )


def _tour_engine(problem: RoutingProblem) -> PlannedAgent:
    return _spawn(
        "tour_engine", "Tour Engine", "tsp", "tour_enum",
        "base specialist: generate candidate loops ranked by cost",
        f"generate and rank candidate loops for {problem.title}",
    )


def _route_validator(problem: RoutingProblem) -> PlannedAgent:
    return _spawn(
        "route_validator", "Route Validator", "validate", "cycle_check",
        "base specialist: prove the loop is Hamiltonian (every city exactly once)",
        f"verify each candidate loop for {problem.title} visits every city exactly once",
    )


def _optimizer(problem: RoutingProblem) -> PlannedAgent:
    return _spawn(
        "optimizer", "Optimizer", "optimize", "prune",
        "added for n>9: enumeration becomes factorial; pool switches to heuristic pruning",
        f"prune the search space for {problem.title} and confirm the cheapest feasible loop",
    )


def _vrp_splitter(problem: RoutingProblem) -> PlannedAgent:
    return _spawn(
        "vrp_splitter", "VRP Splitter", "vrp", "balance_split",
        "VRP detected: partition the city set into two hub-loops",
        f"split {problem.title} into two balanced vehicle routes (max 6 stops each)",
    )


def _vrp_validator(problem: RoutingProblem) -> PlannedAgent:
    return _spawn(
        "vrp_validator", "VRP Validator", "validate", "cycle_check, capacity_check",
        "VRP detected: independently re-check each sub-route is disjoint, in capacity, and covers all",
        f"re-check the two routes for {problem.title}",
    )


def _dependency_checker(problem: RoutingProblem) -> PlannedAgent:
    return _spawn(
        "dependency_checker", "Dependency Checker", "constraints", "order_check",
        "ordering constraints detected: run topological ordering to catch circular dependencies",
        f"detect circular ordering constraints in {problem.title}",
    )


def _order_reviewer(problem: RoutingProblem) -> PlannedAgent:
    return _spawn(
        "order_reviewer", "Order Reviewer", "validate", "order_check, read_back",
        "independently re-verify the dependency verdict without trusting the checker",
        f"independently confirm the ordering verdict for {problem.title}",
    )


def plan_agents(problem: RoutingProblem) -> AgentPlan:
    if problem.precedence:
        plan = (_dependency_checker(problem), _order_reviewer(problem))
        rationale = (
            f"ordering-constraint problem detected -> framework keeps a pool of {len(plan)} agents "
            "(dependency_checker, order_reviewer) to prove contradiction or feasibility"
        )
        return AgentPlan(problem=problem, agents=plan, rationale=rationale)

    if problem.impossible:
        plan = (_graph_builder(problem), _route_validator(problem))
        rationale = (
            f"impossibility problem detected -> framework keeps a pool of {len(plan)} agents "
            "to prove infeasibility (no Hamiltonian cycle) instead of hallucinating a route"
        )
        return AgentPlan(problem=problem, agents=plan, rationale=rationale)

    if problem.kind == "vrp":
        plan = (_vrp_splitter(problem), _vrp_validator(problem))
        rationale = (
            f"VRP detected -> framework scales the pool to {len(plan)} agents "
            "(vrp_splitter, vrp_validator) because one route can no longer be the final answer"
        )
        return AgentPlan(problem=problem, agents=plan, rationale=rationale)

    plan = [_graph_builder(problem), _tour_engine(problem), _route_validator(problem)]
    if len(problem.cities) > 9:
        plan.append(_optimizer(problem))
    plan = tuple(plan)
    rationale = (
        f"n={len(problem.cities)} cities -> framework creates a base pool of {len(plan)} agents "
        "(graph_builder, tour_engine, route_validator)"
        + (
            " + optimizer for combinatorial scale (heuristic mode)"
            if len(problem.cities) > 9
            else " (exact enumeration mode)"
        )
    )
    return AgentPlan(problem=problem, agents=plan, rationale=rationale)