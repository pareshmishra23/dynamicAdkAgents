from __future__ import annotations

import functools
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest

from app.agents.events import ApprovalEventBus, EventStream, WebhookSink
from app.agents.factory import default_agent_factory
from app.agents.langgraph_engine import LangGraphOrchestrator
from app.models import AgentDefinition, AgentLimits, AgentResult, RoutingResult, SelectedAgent
from app.registry.agent_registry import AgentRegistry
from app.registry.client import RegistryClient
from app.registry.policy import PolicyAudit, PolicyEnforcer
from app.registry.pool import DynamicPool
from app.registry.resolver import AgentResolver
from app.tools.registry import default_tool_registry


def _definition(
    agent_id: str,
    *,
    tools: tuple[str, ...] = (),
    version: str = "1.0",
    timeout: int = 60,
    max_tool_calls: int = 5,
    requires_approval: bool = False,
) -> AgentDefinition:
    return AgentDefinition(
        id=agent_id,
        version=version,
        enabled=True,
        name=agent_id,
        description="test agent",
        capabilities=(agent_id,),
        instructions="test agent",
        input_contract={},
        output_contract={"type": "object", "required": ["answer"]},
        allowed_tools=tools,
        limits=AgentLimits(timeout_seconds=timeout, max_tool_calls=max_tool_calls),
        requires_human_approval=requires_approval,
    )


class _RegistryState:
    def __init__(self, agents: dict[str, dict[str, Any]]) -> None:
        self.agents = agents

    def as_list(self) -> list[dict[str, Any]]:
        return [agent for agent in self.agents.values() if agent["enabled"]]

    def as_json(self) -> bytes:
        return json.dumps(self.as_list()).encode()


def _make_stateful_handler(state: _RegistryState):
    class _StatefulHandler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args) -> None:  # noqa: A002
            pass

        def do_GET(self) -> None:  # noqa: N802
            if self.path.startswith("/api/v1/agents"):
                body = state.as_json()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                self.send_response(404)
                self.end_headers()

        def do_PATCH(self) -> None:  # noqa: N802
            agent_id = self.path.split("/")[-2]
            action = self.path.split("/")[-1]
            agent = state.agents.get(agent_id)
            if agent is None:
                self.send_response(404)
                self.end_headers()
            agent["enabled"] = action == "enable"
            body = json.dumps(agent).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_PUT(self) -> None:  # noqa: N802
            agent_id = self.path.split("/")[-1]
            length = int(self.headers["Content-Length"])
            incoming = json.loads(self.rfile.read(length))
            state.agents[agent_id] = incoming
            body = json.dumps(incoming).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return _StatefulHandler


@pytest.fixture()
def pool_fixture():
    agents = {
        "planner": {
            "id": "planner",
            "name": "Planner",
            "description": "plans",
            "capability": "planning",
            "model": "local",
            "enabled": True,
            "config": {"allowed_tools": ["tour_enum"]},
            "policy": {"timeout_seconds": 60, "max_tool_calls": 5},
            "output_contract": {"type": "object", "required": ["answer"]},
            "requires_human_approval": False,
            "version": "1.0",
        },
        "legacy": {
            "id": "legacy",
            "name": "Legacy",
            "description": "old",
            "capability": "review",
            "model": "local",
            "enabled": True,
            "config": {"allowed_tools": []},
            "policy": {"timeout_seconds": 60, "max_tool_calls": 5},
            "output_contract": {"type": "object", "required": ["answer"]},
            "requires_human_approval": False,
            "version": "0.9",
        },
    }
    state = _RegistryState(agents)
    handler = _make_stateful_handler(state)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_address[1]}"
    yield state, url
    server.shutdown()
    thread.join(timeout=2)


class _PostRecorder(BaseHTTPRequestHandler):
    posts: list[dict[str, Any]] = []

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers["Content-Length"])
        body = json.loads(self.rfile.read(length))
        self.__class__.posts.append(body)
        self.send_response(200)
        self.end_headers()

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        pass


@pytest.fixture()
def webhook_url() -> str:
    _PostRecorder.posts = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _PostRecorder)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}/events"
    server.shutdown()
    thread.join(timeout=2)


def test_pool_refresh_adds_new_agents(pool_fixture) -> None:
    state, url = pool_fixture
    initial = _definition("planner")
    pool = DynamicPool(AgentRegistry((initial,)), RegistryClient(url))
    additions = {"planner": {"id": "planner", "name": "Planner", "description": "", "capability": "planning", "model": "", "enabled": True, "config": {"allowed_tools": ["tour_enum"]}, "policy": {}, "requires_human_approval": False, "version": "1.0"}}
    state.agents = additions
    report = pool.refresh()
    assert report.added == ()
    state.agents["reviewer"] = {"id": "reviewer", "name": "Reviewer", "description": "", "capability": "review", "model": "", "enabled": True, "config": {"allowed_tools": []}, "policy": {}, "requires_human_approval": False, "version": "1.1"}
    report = pool.refresh()
    assert report.added == ("reviewer",)
    assert pool.registry.contains("reviewer") is True


def test_pool_refresh_disables_agents_no_longer_present(pool_fixture) -> None:
    state, url = pool_fixture
    pool = DynamicPool(AgentRegistry((_definition("planner"), _definition("legacy"))), RegistryClient(url))
    state.agents.pop("legacy")
    report = pool.refresh()
    assert report.disabled == ("legacy",)
    assert pool.registry.contains("legacy", enabled_only=True) is False
    assert pool.registry.contains("legacy", enabled_only=False) is True


def test_pool_refresh_detects_version_change_and_rollback(pool_fixture) -> None:
    state, url = pool_fixture
    pool = DynamicPool(AgentRegistry((_definition("planner", version="1.0"),)), RegistryClient(url))
    state.agents["planner"]["version"] = "2.0"
    report = pool.refresh()
    assert report.version_changed == ("planner",)
    assert pool.registry.get("planner").version == "2.0"

    previous = _definition("planner", version="1.0")
    pool.rollback_version("planner", previous)
    assert pool.registry.get("planner").version == "1.0"
    updated_state = {k: v for k, v in state.agents.items() if v.get("version") == "1.0"}
    assert any(v["id"] == "planner" and v["version"] == "1.0" for v in state.agents.values())


def test_pool_enable_disable_reaches_registry_and_local(pool_fixture) -> None:
    state, url = pool_fixture
    pool = DynamicPool(AgentRegistry((_definition("planner"),)), RegistryClient(url))
    pool.disable("planner")
    assert pool.registry.contains("planner", enabled_only=True) is False
    assert state.agents["planner"]["enabled"] is False
    pool.enable("planner")
    assert pool.registry.contains("planner", enabled_only=True) is True
    assert state.agents["planner"]["enabled"] is True


def test_policy_blocks_disallowed_tool_with_audit() -> None:
    audit = PolicyAudit()
    enforcer = PolicyEnforcer(default_tool_registry(), audit=audit)
    rogue = _definition("rogue", tools=("websearch",))
    guarded = enforcer.wrap(rogue, default_agent_factory(rogue))
    result = guarded("task")
    assert result.status == "policy_violation"
    assert "not granted" in result.recommendation
    assert any("allowlist violation" in entry for entry in audit.entries)


def test_policy_permits_registered_and_granted_tool() -> None:
    audit = PolicyAudit()
    enforcer = PolicyEnforcer(default_tool_registry(), audit=audit)
    agent = _definition("graph_builder", tools=("matrix_build",))
    guarded = enforcer.wrap(agent, default_agent_factory(agent))
    result = guarded("task")
    assert result.status == "completed"
    assert any("ok" in entry for entry in audit.entries)


def test_policy_enforces_max_tool_calls() -> None:
    audit = PolicyAudit()
    enforcer = PolicyEnforcer(default_tool_registry(), audit=audit)
    agent = _definition("graph_builder", tools=("matrix_build",), max_tool_calls=1)

    def busy(task: str) -> AgentResult:
        return AgentResult(
            agent_id="graph_builder",
            status="completed",
            recommendation="done",
            metadata={"tool_calls": 7},
        )

    result = enforcer.wrap(agent, busy)("task")
    assert result.status == "policy_violation"
    assert "max_tool_calls exceeded" in result.recommendation


def test_policy_enforces_timeout() -> None:
    audit = PolicyAudit()
    enforcer = PolicyEnforcer(default_tool_registry(), audit=audit)
    agent = _definition("graph_builder", tools=("matrix_build",), timeout=1)

    def slow(task: str) -> AgentResult:
        time.sleep(2)
        return AgentResult(agent_id="graph_builder", status="completed", recommendation="late")

    result = enforcer.wrap(agent, slow)("task")
    assert result.status == "policy_violation"
    assert "timeout" in result.recommendation


def test_engine_ends_policy_violation_for_disallowed_tool() -> None:
    rogue = _definition("rogue", tools=("websearch",))
    registry = AgentRegistry((rogue,))
    resolver = AgentResolver(registry, default_agent_factory)
    engine = LangGraphOrchestrator(resolver, policy=PolicyEnforcer(default_tool_registry()), max_iterations=1)
    routing = RoutingResult(selected_agents=(SelectedAgent(agent_id="rogue", reason="r", task="t"),))
    result = engine.start(routing, run_id="policy-run")
    assert result.status == "policy_violation"


def test_approval_events_pending_then_approved(webhook_url: str) -> None:
    events = ApprovalEventBus()
    sink = WebhookSink(webhook_url)
    events.subscribe(sink.record)

    gatekeeper = _definition("gatekeeper", requires_approval=True)
    registry = AgentRegistry((gatekeeper,))
    resolver = AgentResolver(registry, default_agent_factory)
    engine = LangGraphOrchestrator(resolver, events=events, max_iterations=1)
    routing = RoutingResult(selected_agents=(SelectedAgent(agent_id="gatekeeper", reason="g", task="t"),))

    first = engine.start(routing, run_id="approve-run")
    assert first.status == "awaiting_human_approval"
    assert first.pending_approval == "gatekeeper"
    assert [e.kind for e in events.history("approval_pending")] == ["approval_pending"]

    resumed = engine.resume("approve-run", "approved")
    assert resumed.status == "completed"
    assert resumed.approved == ("gatekeeper",)
    assert [e.kind for e in events.history()] == ["approval_pending", "approval_approved"]
    assert any(sink_post["kind"] == "approval_approved" for sink_post in _PostRecorder.posts)


def test_approval_events_pending_then_rejected(webhook_url: str) -> None:
    events = ApprovalEventBus()
    sink = WebhookSink(webhook_url)
    events.subscribe(sink.record)

    gatekeeper = _definition("gatekeeper", requires_approval=True)
    registry = AgentRegistry((gatekeeper,))
    resolver = AgentResolver(registry, default_agent_factory)
    engine = LangGraphOrchestrator(resolver, events=events, max_iterations=1)
    routing = RoutingResult(selected_agents=(SelectedAgent(agent_id="gatekeeper", reason="g", task="t"),))

    first = engine.start(routing, run_id="reject-run")
    assert first.status == "awaiting_human_approval"

    resumed = engine.resume("reject-run", "rejected")
    assert resumed.status == "no_agents_authorized"
    assert resumed.rejected == ("gatekeeper",)
    kinds = [e.kind for e in events.history()]
    assert kinds == ["approval_pending", "approval_rejected"]


def test_event_stream_delivers_events() -> None:
    events = ApprovalEventBus()
    stream = EventStream()
    events.subscribe(stream.record)
    events.pending("r", "a")
    collected = []
    records = iter(stream.events())

    def consume() -> None:
        collected.append(next(records))

    thread = threading.Thread(target=consume)
    thread.start()
    events.approved("r", "a")
    stream.close()
    thread.join(timeout=2)
    assert [(e.kind, e.agent_id) for e in collected] == [("approval_pending", "a")]