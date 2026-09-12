from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from app.agents.factory import AgentAsTool
from app.agents.orchestrator import Critique
from app.models import AgentResult, RoutingResult
from app.registry.resolver import AgentResolver


class OrchestrationState(TypedDict):
    routing: RoutingResult
    approvals: list[str]
    rejections: list[str]
    results: dict[str, AgentResult]
    proposal: str
    verdict: dict[str, Any]
    iterations: int
    status: str
    no_agents: bool


@dataclass(frozen=True)
class EngineResult:
    status: str
    pending_approval: str | None = None
    decision: str | None = None
    results: tuple[AgentResult, ...] = ()
    iterations: int = 0
    approved: tuple[str, ...] = ()
    rejected: tuple[str, ...] = ()


def _default_critic(proposal: str) -> Critique:
    return Critique(valid=proposal != "", issue="", question="")


def _default_refiner(proposal: str, critique: Critique) -> str:
    return proposal


class LangGraphOrchestrator:
    """LangGraph engine for reconciliation: approval gate -> specialists -> critic/refiner loop.

    Used only on the cases that need it (human-in-the-loop and error-recovery);
    the plain Python path in app.agents.orchestrator stays the default.
    """

    def __init__(
        self,
        resolver: AgentResolver,
        *,
        needs_approval: Callable[[str], bool] | None = None,
        critic: Callable[[str], Critique] | None = None,
        refiner: Callable[[str, Critique], str] | None = None,
        max_iterations: int = 3,
        max_parallel_agents: int = 5,
        parallel: bool = True,
    ) -> None:
        if max_iterations < 1:
            raise ValueError("max_iterations must be positive")
        self._resolver = resolver
        self._needs_approval = needs_approval or (lambda agent_id: False)
        self._critic = critic or _default_critic
        self._refiner = refiner or _default_refiner
        self._max_iterations = max_iterations
        self._max_parallel_agents = max_parallel_agents
        self._parallel = parallel
        self._checkpointer = MemorySaver()
        self._compiled = self._build_graph().compile(checkpointer=self._checkpointer)

    def _build_graph(self) -> StateGraph:
        graph = StateGraph(OrchestrationState)
        graph.add_node("approval_gate", self._approval_gate)
        graph.add_node("run_specialists", self._run_specialists)
        graph.add_node("propose", self._propose)
        graph.add_node("critic", self._critic_node)
        graph.add_node("refine", self._refine)
        graph.add_node("finalize", self._finalize)
        graph.add_edge(START, "approval_gate")
        graph.add_edge("approval_gate", "run_specialists")
        graph.add_edge("run_specialists", "propose")
        graph.add_conditional_edges(
            "propose",
            self._route_after_propose,
            {"finalize": "finalize", "critic": "critic"},
        )
        graph.add_conditional_edges(
            "critic",
            self._route_critic,
            {"finalize": "finalize", "refine": "refine"},
        )
        graph.add_edge("refine", "critic")
        graph.add_edge("finalize", END)
        return graph

    def _config(self, run_id: str) -> dict:
        return {
            "configurable": {"thread_id": run_id},
            "recursion_limit": 50,
        }

    def start(self, routing: RoutingResult, run_id: str = "run-default") -> EngineResult:
        initial: OrchestrationState = {
            "routing": routing,
            "approvals": [],
            "rejections": [],
            "results": {},
            "proposal": "",
            "verdict": {"valid": False, "issue": ""},
            "iterations": 0,
            "status": "running",
            "no_agents": False,
        }
        result = self._compiled.invoke(initial, self._config(run_id))
        return self._interpret(run_id, result)

    def resume(self, run_id: str, action: str) -> EngineResult:
        result = self._compiled.invoke(Command(resume=action), self._config(run_id))
        return self._interpret(run_id, result)

    def _interpret(self, run_id: str, result: dict[str, Any]) -> EngineResult:
        pending = None
        for item in result.get("__interrupt__", []):
            pending = item.value.get("agent_id", pending)
            break
        if pending is not None:
            return EngineResult(status="awaiting_human_approval", pending_approval=pending)
        values = self._compiled.get_state(self._config(run_id)).values
        return EngineResult(
            status=values.get("status", "completed"),
            decision=values.get("proposal"),
            results=tuple(values.get("results", {}).values()),
            iterations=values.get("iterations", 0),
            approved=tuple(values.get("approvals", [])),
            rejected=tuple(values.get("rejections", [])),
        )

    def _approval_gate(self, state: OrchestrationState) -> dict[str, Any]:
        approvals = list(state.get("approvals", []))
        rejections = list(state.get("rejections", []))
        for item in state["routing"].selected_agents:
            if item.agent_id in approvals or item.agent_id in rejections:
                continue
            if self._needs_approval(item.agent_id):
                decision = interrupt({"type": "human_approval", "agent_id": item.agent_id})
                (approvals if decision == "approved" else rejections).append(item.agent_id)
        return {"approvals": approvals, "rejections": rejections}

    def _selected_pairs(self, state: OrchestrationState) -> list[tuple[AgentAsTool, Any]]:
        pairs = []
        for item in state["routing"].selected_agents:
            if item.agent_id in state.get("rejections", []):
                continue
            resolved = self._resolver.resolve(item.agent_id)
            pairs.append((AgentAsTool(item.agent_id, resolved.execute), item))
        return pairs

    def _run_specialists(self, state: OrchestrationState) -> dict[str, Any]:
        pairs = self._selected_pairs(state)
        if self._parallel and 1 < len(pairs) <= self._max_parallel_agents:
            with ThreadPoolExecutor(max_workers=len(pairs)) as executor:
                futures = [executor.submit(tool, item.task) for tool, item in pairs]
                results = [future.result() for future in futures]
        else:
            results = [tool(item.task) for tool, item in pairs]
        return {"results": {result.agent_id: result for result in results}}

    def _propose(self, state: OrchestrationState) -> dict[str, Any]:
        results = state.get("results", {})
        if not results:
            return {"proposal": "NO_AUTHORIZED_AGENTS", "no_agents": True}
        merged = " | ".join(result.recommendation for result in results.values())
        return {"proposal": f"Integrated decision: {merged}"}

    def _critic_node(self, state: OrchestrationState) -> dict[str, Any]:
        critique = self._critic(state.get("proposal", ""))
        return {
            "verdict": {"valid": bool(critique.valid), "issue": critique.issue},
            "iterations": state.get("iterations", 0) + 1,
        }

    def _route_after_propose(self, state: OrchestrationState) -> str:
        return "finalize" if state.get("no_agents") else "critic"

    def _route_critic(self, state: OrchestrationState) -> str:
        if state["verdict"]["valid"] or state["iterations"] >= self._max_iterations:
            return "finalize"
        return "refine"

    def _refine(self, state: OrchestrationState) -> dict[str, Any]:
        critique = Critique(
            valid=state["verdict"]["valid"], issue=state["verdict"]["issue"], question=""
        )
        return {"proposal": self._refiner(state.get("proposal", ""), critique)}

    def _finalize(self, state: OrchestrationState) -> dict[str, Any]:
        if state.get("no_agents"):
            return {"status": "no_agents_authorized"}
        if state["verdict"]["valid"]:
            return {"status": "completed"}
        return {"status": "abstain_human_review"}