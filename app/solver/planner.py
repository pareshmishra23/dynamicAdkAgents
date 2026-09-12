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
        f"enumerate candidate loops for {problem.title} and rank them",
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
        "added for n>8: combinatorial blow-up needs pruning, not enumeration",
        f"prune the search space for {problem.title} and pick the cheapest feasible loop",
    )


def plan_agents(problem: RoutingProblem) -> AgentPlan:
    if problem.impossible:
        plan = (
            _graph_builder(problem),
            _route_validator(problem),
        )
        rationale = (
            f"impossible problem detected -> framework keeps a pool of {len(plan)} agents "
            "to prove infeasibility instead of hallucinating a route"
        )
    else:
        plan = [_graph_builder(problem), _tour_engine(problem), _route_validator(problem)]
        if len(problem.cities) > 8:
            plan.append(_optimizer(problem))
        plan = tuple(plan)
        rationale = (
            f"n={len(problem.cities)} cities classified small -> framework creates a base pool "
            f"of {len(plan)} agents (graph_builder, tour_engine, route_validator)"
            + (" + optimizer for combinatorial scale" if len(problem.cities) > 8 else "")
        )
    return AgentPlan(problem=problem, agents=plan, rationale=rationale)