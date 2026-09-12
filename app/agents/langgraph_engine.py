from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from app.agents.factory import AgentAsTool
from app.agents.orchestrator import Critique
from app.agents.traces import ThinkTracer
from app.models import AgentResult, RoutingResult, SelectedAgent
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
    trace: tuple[str, ...] = ()


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
        trace: ThinkTracer | None = None,
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
        self._tracer = trace
        serde = JsonPlusSerializer(allowed_msgpack_modules=[SelectedAgent, RoutingResult, AgentResult])
        self._checkpointer = MemorySaver(serde=serde)
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
        if self._tracer:
            self._tracer.think(f"run={run_id} -> routing {len(routing.selected_agents)} candidate agents")
            for item in routing.selected_agents:
                self._tracer.pointer(f"selected {item.agent_id}: reason={item.reason!r} task={item.task!r}")
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
        status = values.get("status", "completed")
        iterations = values.get("iterations", 0)
        if self._tracer:
            self._tracer.decide(f"status={status} iterations={iterations}")
        return EngineResult(
            status=status,
            decision=values.get("proposal"),
            results=tuple(values.get("results", {}).values()),
            iterations=iterations,
            approved=tuple(values.get("approvals", [])),
            rejected=tuple(values.get("rejections", [])),
            trace=self._tracer.steps if self._tracer else (),
        )

    def _approval_gate(self, state: OrchestrationState) -> dict[str, Any]:
        approvals = list(state.get("approvals", []))
        rejections = list(state.get("rejections", []))
        for item in state["routing"].selected_agents:
            if item.agent_id in approvals or item.agent_id in rejections:
                continue
            if self._needs_approval(item.agent_id):
                if self._tracer:
                    self._tracer.escalate(
                        f"human approval required for {item.agent_id} -> pausing at interrupt gate"
                    )
                decision = interrupt({"type": "human_approval", "agent_id": item.agent_id})
                (approvals if decision == "approved" else rejections).append(item.agent_id)
            elif self._tracer:
                self._tracer.think(f"{item.agent_id} auto-approved (no approval policy)")
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
        if self._tracer:
            for tool, item in pairs:
                definition = self._resolver.resolve(item.agent_id).definition
                tools = ", ".join(definition.allowed_tools) or "(none)"
                self._tracer.pointer(
                    f"{item.agent_id} v{definition.version} -> capabilities={list(definition.capabilities)} "
                    f"| tools=[{tools}] | contract={definition.output_contract or '(none)'}"
                )
        if self._parallel and 1 < len(pairs) <= self._max_parallel_agents:
            with ThreadPoolExecutor(max_workers=len(pairs)) as executor:
                futures = []
                for tool, item in pairs:
                    def run(agent_tool=tool, task=item.task) -> AgentResult:
                        if self._tracer:
                            self._tracer.act(f"{agent_tool.agent_id} executing task={task!r}")
                        return agent_tool(task)

                    futures.append(executor.submit(run))
                results = [future.result() for future in futures]
        else:
            results = []
            for tool, item in pairs:
                started = time.perf_counter()
                if self._tracer:
                    self._tracer.act(f"{tool.agent_id} executing task={item.task!r}")
                result = tool(item.task)
                results.append(result)
                self._trace_result(result, started)
        output = {result.agent_id: result for result in results}
        if self._tracer:
            for result in results:
                self._tracer.verify(
                    f"{result.agent_id} -> {result.status} | evidence={len(result.evidence)} value={result.recommendation!r}"
                )
                if result.metadata.get("thinking"):
                    self._tracer.think(f"{result.agent_id} thought: {result.metadata['thinking']}")
        return {"results": output}

    def _trace_result(self, result: AgentResult, started: float) -> None:
        if self._tracer:
            self._tracer.verify(f"{result.agent_id} -> {result.status} in {self._tracer.runtime_ms(started)}")

    def _propose(self, state: OrchestrationState) -> dict[str, Any]:
        results = state.get("results", {})
        if not results:
            if self._tracer:
                self._tracer.think("no authorized agents remain -> terminating run")
            return {"proposal": "NO_AUTHORIZED_AGENTS", "no_agents": True}
        if self._tracer:
            self._tracer.think(f"integrating {len(results)} specialist results into one decision")
        merged = " | ".join(result.recommendation for result in results.values())
        return {"proposal": f"Integrated decision: {merged}"}

    def _critic_node(self, state: OrchestrationState) -> dict[str, Any]:
        critique = self._critic(state.get("proposal", ""))
        if self._tracer:
            self._tracer.critic(
                f"iteration {state.get('iterations', 0) + 1} -> valid={bool(critique.valid)} issue={critique.issue!r}"
            )
        return {
            "verdict": {"valid": bool(critique.valid), "issue": critique.issue},
            "iterations": state.get("iterations", 0) + 1,
        }

    def _route_after_propose(self, state: OrchestrationState) -> str:
        return "finalize" if state.get("no_agents") else "critic"

    def _route_critic(self, state: OrchestrationState) -> str:
        if state["verdict"]["valid"]:
            if self._tracer:
                self._tracer.think("verdict valid -> accepting proposal")
            return "finalize"
        if state["iterations"] >= self._max_iterations:
            if self._tracer:
                self._tracer.escalate(
                    f"critic loop exhausted at iteration {state['iterations']} >= max_iterations={self._max_iterations} "
                    "-> abstain_human_review"
                )
            return "finalize"
        if self._tracer:
            self._tracer.think("verdict invalid -> sending to refiner for another pass")
        return "refine"

    def _refine(self, state: OrchestrationState) -> dict[str, Any]:
        critique = Critique(
            valid=state["verdict"]["valid"], issue=state["verdict"]["issue"], question=""
        )
        updated = self._refiner(state.get("proposal", ""), critique)
        if self._tracer:
            self._tracer.think(f"refiner applied: proposal updated to {updated!r}")
        return {"proposal": updated}

    def _finalize(self, state: OrchestrationState) -> dict[str, Any]:
        if state.get("no_agents"):
            return {"status": "no_agents_authorized"}
        if state["verdict"]["valid"]:
            return {"status": "completed"}
        return {"status": "abstain_human_review"}