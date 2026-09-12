import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from app.models import AgentDefinition
from app.registry.policy import PolicyAudit, PolicyEnforcer
from app.tools.registry import DEFAULT_TOOL_SPECS, default_tool_registry
from app.tools.web import granted_tools, search_web, websearch_handler, webfetch_handler


class _StubHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        if self.path == "/search":
            payload = {
                "items": [
                    {"title": "Flatiron District", "url": "https://flatiron.example", "snippet": f"district near {body.get('query')}"}
                ]
            }
            data = json.dumps(payload).encode()
        else:
            data = b"{}"
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/page":
            data = b"<html><body><h1>Flatiron</h1><p>10 blocks from office</p></body></html>"
        else:
            data = b"{}"
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


@pytest.fixture
def stub_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _StubHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()


def defn(agent_id, allowed_tools=()):
    return AgentDefinition(
        id=agent_id,
        version="v1",
        enabled=True,
        name=agent_id,
        description="research",
        capabilities=("research",),
        instructions="research",
        input_contract={},
        output_contract={"type": "object", "properties": {}},
        allowed_tools=tuple(allowed_tools),
    )


class TestRegistryBoundary:
    def test_search_granted_only_to_research(self):
        reg = default_tool_registry()
        assert reg.allowed_for("websearch", "research_agent")
        assert reg.allowed_for("webfetch", "research_agent")
        assert not reg.allowed_for("websearch", "taxi_agent")
        assert not reg.allowed_for("websearch", "no_such")

    def test_granted_tools_only_returns_grants(self):
        assert set(granted_tools(defn("research_agent", ("websearch", "webfetch")))) == {"websearch", "webfetch"}
        assert granted_tools(defn("taxi_agent", ("matrix_build",))) == {}

    def test_specs_expose_real_handlers(self):
        specs = {s.name: s for s in DEFAULT_TOOL_SPECS}
        assert specs["websearch"].handler is websearch_handler
        assert specs["webfetch"].handler is webfetch_handler


class TestOfflineDefault:
    def test_search_unavailable_offline(self, monkeypatch):
        monkeypatch.delenv("WEBSEARCH_PROVIDER", raising=False)
        result = websearch_handler(query="hotels new york")
        assert result["status"] == "unavailable"
        assert result["items"] == []
        assert "WEBSEARCH_PROVIDER" in result["note"]

    def test_fetch_rejects_non_http(self, monkeypatch):
        monkeypatch.delenv("HTTP_FETCH_TIMEOUT", raising=False)
        result = webfetch_handler(url="file:///etc/passwd")
        assert result["status"] == "unavailable"


class TestHttpProvider:
    def test_search_parses_items(self, stub_server, monkeypatch):
        monkeypatch.setenv("WEBSEARCH_PROVIDER", "http")
        monkeypatch.setenv("WEBSEARCH_ENDPOINT", f"{stub_server}/search")
        result = search_web("flatiron")
        assert result["status"] == "ok"
        assert result["items"][0]["title"] == "Flatiron District"

    def test_fetch_snapshots_text(self, stub_server, monkeypatch):
        monkeypatch.setenv("HTTP_FETCH_TIMEOUT", "10")
        result = webfetch_handler(url=f"{stub_server}/page")
        assert result["status"] == "ok"
        assert "Flatiron" in result["content"]
        assert "10 blocks" in result["content"]


class TestPolicyEnforcementAtBoundary:
    def test_granted_research_agent_passes(self):
        enforcer = PolicyEnforcer(default_tool_registry(), PolicyAudit())
        research = defn("research_agent", ("websearch",))

        def execute(task):
            handlers = granted_tools(research)
            assert "websearch" in handlers
            return handlers["websearch"] and __import__("app.models", fromlist=["AgentResult"]).AgentResult(
                agent_id="research_agent", status="completed", recommendation="live data fetched",
                evidence=("websearch",),
            )

        result = enforcer.wrap(research, execute)("task")
        assert result.status == "completed"

    def test_ungranted_agent_gets_violation(self):
        enforcer = PolicyEnforcer(default_tool_registry(), PolicyAudit())
        rogue = defn("taxi_agent", ("websearch",))
        result = enforcer.wrap(rogue, lambda task: None)("task")
        assert result.status == "policy_violation"
        assert "not granted" in result.recommendation