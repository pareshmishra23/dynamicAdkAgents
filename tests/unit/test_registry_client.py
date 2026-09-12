from __future__ import annotations

import functools
import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from app.agents.factory import default_agent_factory
from app.agents.langgraph_engine import LangGraphOrchestrator
from app.models import RoutingResult, SelectedAgent
from app.registry.agent_registry import AgentRegistry
from app.registry.client import (
    RegistryClient,
    RegistryMappingError,
    RegistryUnavailable,
    map_mcp_server,
    map_registry_agent,
)
from app.registry.resolver import AgentResolver

FIXTURES = {
    "agents": [
        {
            "id": "planning_agent",
            "name": "Planning Agent",
            "description": "Plans the lean trip",
            "capability": "planning",
            "model": "gemini-2.5-flash",
            "enabled": True,
            "config": {"allowed_tools": ["matrix_build", "websearch"]},
            "policy": {"temperature": 0.0, "max_tool_calls": 9, "timeout_seconds": 30},
            "output_contract": {"type": "object", "required": ["matrix", "options"]},
            "requires_human_approval": False,
            "version": "2.1",
        },
        {
            "id": "signoff_agent",
            "name": "Signoff Agent",
            "description": "Must be human-approved before booking",
            "capability": "booking",
            "model": "gemini-2.5-pro",
            "enabled": True,
            "config": {},
            "policy": {"temperature": 0.0, "max_iterations": 2},
            "output_contract": {"type": "object", "required": ["confirmation"]},
            "requires_human_approval": True,
            "version": "1.0",
        },
    ],
    "mcp": [
        {
            "id": "travel-tools",
            "name": "Travel Tools",
            "description": "Flights, hotels, cabs",
            "endpoint": "stdio://travel",
            "transport": "stdio",
            "enabled": True,
            "version": "1.0",
        },
        {
            "id": "dead-server",
            "name": "Dead Server",
            "endpoint": "http://localhost:1",
            "transport": "http",
            "enabled": False,
            "version": "0.9",
        },
    ],
}


class _Handler(BaseHTTPRequestHandler):
    routes: dict[str, bytes] = {}

    def do_GET(self) -> None:  # noqa: N802 (stdlib naming)
        body = self.routes.get(self.path)
        if body is None:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        pass


@pytest.fixture()
def registry_url() -> str:
    handler = functools.partial(_Handler)
    _Handler.routes = {
        "/api/v1/agents?enabled=true": json.dumps(FIXTURES["agents"]).encode(),
        "/api/v1/mcp-servers?enabled=true": json.dumps(FIXTURES["mcp"]).encode(),
    }
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    thread.join(timeout=2)


def test_client_fetches_enabled_agents(registry_url: str) -> None:
    definitions = RegistryClient(registry_url).fetch_enabled_agents()
    assert [d.id for d in definitions] == ["planning_agent", "signoff_agent"]


def test_client_maps_policy_contract_and_approval_flags(registry_url: str) -> None:
    definitions = {d.id: d for d in RegistryClient(registry_url).fetch_enabled_agents()}
    planning = definitions["planning_agent"]
    assert planning.model == "gemini-2.5-flash"
    assert planning.version == "2.1"
    assert planning.capabilities == ("planning",)
    assert planning.allowed_tools == ("matrix_build", "websearch")
    assert planning.limits.max_tool_calls == 9
    assert planning.limits.timeout_seconds == 30
    assert planning.policy["temperature"] == 0.0
    assert planning.output_contract["required"] == ["matrix", "options"]
    assert planning.requires_human_approval is False


def test_client_marks_required_human_approval(registry_url: str) -> None:
    definitions = {d.id: d for d in RegistryClient(registry_url).fetch_enabled_agents()}
    assert definitions["signoff_agent"].requires_human_approval is True


def test_client_fetches_enabled_mcp_servers(registry_url: str) -> None:
    servers = RegistryClient(registry_url).fetch_enabled_mcp_servers()
    assert [s.id for s in servers] == ["travel-tools"]
    assert servers[0].endpoint == "stdio://travel"
    assert servers[0].transport == "stdio"


def test_client_skips_disabled_servers_even_if_returned(registry_url: str) -> None:
    servers = RegistryClient(registry_url).fetch_enabled_mcp_servers()
    assert all(s.enabled for s in servers)
    assert "dead-server" not in [s.id for s in servers]


def test_client_fails_closed_on_http_error() -> None:
    handler = functools.partial(_Handler)
    _Handler.routes = {}
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        with pytest.raises(RegistryUnavailable):
            RegistryClient(url).fetch_enabled_agents()
    finally:
        server.shutdown()
        thread.join(timeout=2)


def test_client_fails_closed_when_server_down() -> None:
    with pytest.raises(RegistryUnavailable):
        RegistryClient("http://127.0.0.1:1").fetch_enabled_agents()


def test_map_registry_agent_rejects_bad_payload() -> None:
    with pytest.raises(RegistryMappingError):
        map_registry_agent({"name": "no id"})
    with pytest.raises(RegistryMappingError):
        map_registry_agent({"id": "x"})


def test_map_mcp_server_rejects_bad_payload() -> None:
    with pytest.raises(RegistryMappingError):
        map_mcp_server({"id": "x"})


def test_approval_flag_gates_langgraph_execution() -> None:
    definitions = tuple(map_registry_agent(item) for item in FIXTURES["agents"])
    registry = AgentRegistry(definitions)
    resolver = AgentResolver(registry, default_agent_factory)
    engine = LangGraphOrchestrator(resolver, max_iterations=1)
    routing = RoutingResult(
        selected_agents=(
            SelectedAgent(agent_id="planning_agent", reason="plan", task="plan lean trip"),
            SelectedAgent(agent_id="signoff_agent", reason="approve", task="sign off booking"),
        )
    )
    result = engine.start(routing, run_id="bead2-approval")
    assert result.status == "awaiting_human_approval"
    assert result.pending_approval == "signoff_agent"


def test_approval_flag_skipped_when_not_required() -> None:
    definitions = tuple(map_registry_agent(item) for item in FIXTURES["agents"][:1])
    registry = AgentRegistry(definitions)
    resolver = AgentResolver(registry, default_agent_factory)
    engine = LangGraphOrchestrator(resolver, max_iterations=1)
    routing = RoutingResult(
        selected_agents=(SelectedAgent(agent_id="planning_agent", reason="plan", task="plan lean trip"),)
    )
    result = engine.start(routing, run_id="bead2-no-approval")
    assert result.status == "completed"
    assert result.pending_approval is None