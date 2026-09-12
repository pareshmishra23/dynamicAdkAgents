from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from app.agents.langgraph_engine import EngineResult, LangGraphOrchestrator
from app.agents.traces import ThinkTracer
from app.models import RoutingResult, SelectedAgent
from app.registry.agent_registry import AgentRegistry
from app.registry.resolver import AgentResolver
from app.solver.factory import build_solver_factory
from app.solver.planner import plan_agents
from app.solver.problems import RoutingProblem


@dataclass(frozen=True)
class SolutionRun:
    problem: RoutingProblem
    decided_agents: tuple[str, ...]
    rationale: str
    result: EngineResult
    duration_ms: float

    def passed(self) -> bool:
        if self.problem.impossible or self.problem.precedence:
            lowered = (self.result.decision or "").lower()
            return self.result.status == "completed" and (
                "impossible" in lowered or "circular" in lowered
            )
        if self.problem.expected is None:
            return self.result.status == "completed" and "impossible" not in (self.result.decision or "").lower()
        return (
            self.result.status == "completed"
            and all(city in self.result.decision for city in self.problem.expected)
            and self.problem.expected_cost is not None
            and f"{self.problem.expected_cost:g}" in self.result.decision
        )


def solve_problem(
    problem: RoutingProblem,
    *,
    trace: ThinkTracer | None = None,
    log_dir: Path | None = None,
    agent_factory=None,
) -> SolutionRun:
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
    factory = agent_factory or build_solver_factory(problem, trace=trace)
    resolver = AgentResolver(registry, factory)
    routing = RoutingResult(
        selected_agents=tuple(
            SelectedAgent(agent_id=planned.definition.id, reason=planned.reason, task=planned.task)
            for planned in plan.agents
        )
    )
    engine = LangGraphOrchestrator(resolver, trace=trace, max_iterations=2)
    started = time.perf_counter()
    result = engine.start(routing, run_id=f"problem-{problem.id}")
    duration_ms = (time.perf_counter() - started) * 1000

    if log_dir is not None and trace is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / f"problem_{problem.id}.log").write_text(
            "\n".join(trace.steps) + "\n", encoding="utf-8"
        )

    return SolutionRun(
        problem=problem,
        decided_agents=tuple(planned.definition.id for planned in plan.agents),
        rationale=plan.rationale,
        result=result,
        duration_ms=round(duration_ms, 1),
    )