from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Callable

from app.agents.factory import AgentAsTool
from app.models import AgentResult, RoutingResult
from app.registry.resolver import AgentResolver


class OrchestrationError(RuntimeError):
    pass


@dataclass(frozen=True)
class OrchestrationResult:
    status: str
    specialist_results: tuple[AgentResult, ...]
    final_decision: str
    iterations: int = 0
    trace: tuple[str, ...] = ()


class Orchestrator:
    """Owns integration and the final decision; specialists only provide results."""

    def __init__(self, resolver: AgentResolver, max_parallel_agents: int = 5) -> None:
        self.resolver = resolver
        self.max_parallel_agents = max_parallel_agents

    def selected_tools(self, routing: RoutingResult) -> tuple[AgentAsTool, ...]:
        return tuple(
            AgentAsTool(item.agent_id, self.resolver.resolve(item.agent_id).execute)
            for item in routing.selected_agents
        )

    def execute_parallel(self, routing: RoutingResult) -> tuple[AgentResult, ...]:
        tools = self.selected_tools(routing)
        if len(tools) > self.max_parallel_agents:
            raise OrchestrationError("parallel agent limit exceeded")
        with ThreadPoolExecutor(max_workers=len(tools) or 1) as executor:
            futures = [executor.submit(tool, item.task) for tool, item in zip(tools, routing.selected_agents)]
            return tuple(future.result() for future in futures)

    def execute_sequential(self, routing: RoutingResult) -> tuple[AgentResult, ...]:
        results = []
        for tool, item in zip(self.selected_tools(routing), routing.selected_agents):
            results.append(tool(item.task))
        return tuple(results)

    def integrate(self, results: tuple[AgentResult, ...]) -> str:
        if not results:
            raise OrchestrationError("cannot integrate empty specialist results")
        return "Integrated decision: " + " | ".join(result.recommendation for result in results)

    def run(self, routing: RoutingResult, *, parallel: bool = True) -> OrchestrationResult:
        results = self.execute_parallel(routing) if parallel else self.execute_sequential(routing)
        return OrchestrationResult(
            status="completed",
            specialist_results=results,
            final_decision=self.integrate(results),
            trace=("router", "agent_registry", "agent_as_tool", "parallel" if parallel else "sequential", "orchestrator"),
        )


@dataclass(frozen=True)
class Critique:
    valid: bool
    issue: str
    question: str


class BoundedRefiner:
    """Planner -> critic -> refiner loop with a hard iteration limit."""

    def __init__(self, critic: Callable[[str], Critique], refiner: Callable[[str, Critique], str], max_iterations: int = 3) -> None:
        if max_iterations < 1:
            raise ValueError("max_iterations must be positive")
        self.critic = critic
        self.refiner = refiner
        self.max_iterations = max_iterations

    def run(self, proposal: str) -> tuple[str, int, str]:
        current = proposal
        for iteration in range(1, self.max_iterations + 1):
            critique = self.critic(current)
            if critique.valid:
                return current, iteration, "completed"
            current = self.refiner(current, critique)
        return current, self.max_iterations, "abstain_human_review"
