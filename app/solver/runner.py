from __future__ import annotations

from dataclasses import dataclass

from app.agents.langgraph_engine import EngineResult, LangGraphOrchestrator
from app.agents.traces import ThinkTracer
from app.models import RoutingResult, SelectedAgent
from app.registry.agent_registry import AgentRegistry
from app.registry.resolver import AgentResolver
from app.solver.agents import make_solver_factory
from app.solver.planner import plan_agents
from app.solver.problems import RoutingProblem


@dataclass(frozen=True)
class SolutionRun:
    problem: RoutingProblem
    decided_agents: tuple[str, ...]
    rationale: str
    result: EngineResult

    def passed(self) -> bool:
        if self.problem.impossible:
            return self.result.status == "completed" and "impossible" in self.result.decision
        if self.problem.expected is None:
            return False
        return (
            self.result.status == "completed"
            and all(city in self.result.decision for city in self.problem.expected)
            and self.problem.expected_cost is not None
            and f"{self.problem.expected_cost:g}" in self.result.decision
        )


def solve_problem(problem: RoutingProblem, *, trace: ThinkTracer | None = None) -> SolutionRun:
    plan = plan_agents(problem)
    if trace:
        trace.think(f"deciding agent pool for problem {problem.id}: {problem.title}")
        trace.think(plan.rationale)
        for planned in plan.agents:
            trace.pointer(
                f"framework creates agent {planned.definition.id} -> {planned.reason} | "
                f"task={planned.task!r}"
            )
    registry = AgentRegistry(tuple(planned.definition for planned in plan.agents))
    resolver = AgentResolver(registry, make_solver_factory(problem))
    routing = RoutingResult(
        selected_agents=tuple(
            SelectedAgent(agent_id=planned.definition.id, reason=planned.reason, task=planned.task)
            for planned in plan.agents
        )
    )

    engine = LangGraphOrchestrator(resolver, trace=trace, max_iterations=2)
    result = engine.start(routing, run_id=f"problem-{problem.id}")
    return SolutionRun(
        problem=problem,
        decided_agents=tuple(planned.definition.id for planned in plan.agents),
        rationale=plan.rationale,
        result=result,
    )