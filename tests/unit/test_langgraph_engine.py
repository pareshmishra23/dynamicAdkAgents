from __future__ import annotations

import pytest

langgraph = pytest.importorskip("langgraph")

from app.agents.factory import default_agent_factory  # noqa: E402
from app.agents.langgraph_engine import LangGraphOrchestrator  # noqa: E402
from app.agents.orchestrator import Critique  # noqa: E402
from app.agents.traces import ThinkTracer  # noqa: E402
from app.models import AgentDefinition, AgentLimits, RoutingResult, SelectedAgent  # noqa: E402
from app.registry.agent_registry import AgentRegistry  # noqa: E402
from app.registry.resolver import AgentResolver  # noqa: E402


def _definition(agent_id: str, name: str, capability: str) -> AgentDefinition:
    return AgentDefinition(
        id=agent_id,
        version="1.0",
        enabled=True,
        name=name,
        description=f"{name} for {capability}",
        capabilities=(capability,),
        instructions=f"You are the {name}.",
        input_contract={},
        output_contract={},
        allowed_tools=(),
        limits=AgentLimits(),
    )


def _resolver() -> AgentResolver:
    registry = AgentRegistry(
        (
            _definition("taxi_agent", "Taxi Agent", "taxi"),
            _definition("car_agent", "Car Agent", "car-rental"),
        )
    )
    return AgentResolver(registry, default_agent_factory)


def _routing(*items: tuple[str, str, str]) -> RoutingResult:
    return RoutingResult(
        selected_agents=tuple(
            SelectedAgent(agent_id=agent_id, reason=reason, task=task)
            for agent_id, reason, task in items
        )
    )


def _engine(*, needs_approval=None, critic=None, refiner=None, max_iterations=3, trace=None) -> LangGraphOrchestrator:
    return LangGraphOrchestrator(
        _resolver(),
        needs_approval=needs_approval,
        critic=critic,
        refiner=refiner,
        max_iterations=max_iterations,
        trace=trace,
    )


def test_run_without_approval_completes() -> None:
    engine = _engine()
    routing = _routing(
        ("taxi_agent", "taxi requested", "book a taxi"),
        ("car_agent", "car rental wanted", "rent a car"),
    )
    result = engine.start(routing)
    assert result.status == "completed"
    assert result.decision is not None
    assert {r.agent_id for r in result.results} == {"taxi_agent", "car_agent"}


def test_human_approval_pauses_and_resumes() -> None:
    engine = _engine(needs_approval=lambda agent_id: agent_id == "taxi_agent")
    routing = _routing(
        ("taxi_agent", "taxi requested", "book a taxi"),
        ("car_agent", "car rental wanted", "rent a car"),
    )

    first = engine.start(routing, run_id="run-hitl")
    assert first.status == "awaiting_human_approval"
    assert first.pending_approval == "taxi_agent"

    resumed = engine.resume("run-hitl", "approved")
    assert resumed.status == "completed"
    assert "taxi_agent" in resumed.approved
    assert {r.agent_id for r in resumed.results} == {"taxi_agent", "car_agent"}


def test_rejected_agent_is_excluded() -> None:
    engine = _engine(needs_approval=lambda agent_id: agent_id == "taxi_agent")
    routing = _routing(
        ("taxi_agent", "taxi requested", "book a taxi"),
        ("car_agent", "car rental wanted", "rent a car"),
    )
    engine.start(routing, run_id="run-reject")
    resumed = engine.resume("run-reject", "rejected")
    assert resumed.status == "completed"
    assert "taxi_agent" in resumed.rejected
    assert {r.agent_id for r in resumed.results} == {"car_agent"}


def test_all_rejected_yields_no_agents_authorized() -> None:
    engine = _engine(needs_approval=lambda agent_id: True)
    routing = _routing(
        ("taxi_agent", "taxi requested", "book a taxi"),
        ("car_agent", "car rental wanted", "rent a car"),
    )
    engine.start(routing, run_id="run-none")
    engine.resume("run-none", "rejected")
    resumed = engine.resume("run-none", "rejected")
    assert resumed.status == "no_agents_authorized"


def test_critic_refiner_loop_is_bounded() -> None:
    def strict_critic(proposal: str) -> Critique:
        return Critique(valid=False, issue="needs refinement", question="")

    def refiner(proposal: str, critique: Critique) -> str:
        return proposal + "~v"

    engine = _engine(critic=strict_critic, refiner=refiner, max_iterations=2)
    routing = _routing(("taxi_agent", "taxi requested", "book a taxi"))
    result = engine.start(routing)
    assert result.status == "abstain_human_review"
    assert result.iterations == 2


def test_critic_accepts_after_refinement() -> None:
    def critic(proposal: str) -> Critique:
        return Critique(valid="~v" in proposal, issue="improve", question="")

    def refiner(proposal: str, critique: Critique) -> str:
        return proposal + "~v"

    engine = _engine(critic=critic, refiner=refiner, max_iterations=3)
    routing = _routing(("taxi_agent", "taxi requested", "book a taxi"))
    result = engine.start(routing)
    assert result.status == "completed"
    assert result.decision.endswith("~v")
    assert result.iterations == 2


def test_engine_emits_thinking_trace() -> None:
    tracer = ThinkTracer(enabled=False)
    engine = _engine(trace=tracer)
    routing = _routing(("taxi_agent", "taxi requested", "book a taxi"))
    result = engine.start(routing)

    points = "\n".join(result.trace)
    assert "[think] run=" in points
    assert "[pointer] selected taxi_agent: reason='taxi requested'" in points
    assert "[pointer] taxi_agent v1.0 -> capabilities=['taxi']" in points
    assert "[act] taxi_agent executing task='book a taxi'" in points
    assert "[verify] taxi_agent -> completed" in points
    assert "[critic] iteration 1 -> valid=True" in points
    assert "[decide] status=completed" in points


def test_rejection_path_is_traced() -> None:
    tracer = ThinkTracer(enabled=False)
    engine = _engine(trace=tracer, needs_approval=lambda agent_id: agent_id == "taxi_agent")
    routing = _routing(("taxi_agent", "taxi requested", "book a taxi"))
    first = engine.start(routing, run_id="run-trace-reject")
    assert first.status == "awaiting_human_approval"
    engine.resume("run-trace-reject", "rejected")

    points = "\n".join(tracer.steps)
    assert "[escalate] human approval required for taxi_agent" in points
    assert "[think] no authorized agents remain" in points