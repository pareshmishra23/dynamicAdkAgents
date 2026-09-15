from __future__ import annotations

import json
import pytest

from app.analyzer.task_analyzer import (
    InvalidCapabilityError,
    SecurityPolicyViolation,
    TaskAnalyzer,
)
from app.agents.factory import default_agent_factory
from app.agents.orchestrator import Critique, Orchestrator
from app.models import AgentDefinition, AgentLimits, AgentResult, RoutingResult, SelectedAgent
from app.registry.agent_registry import (
    AgentDisabledError,
    AgentNotFoundError,
    AgentRegistry,
    RegistryError,
)
from app.registry.capability import (
    CapabilityNotFoundError,
    CapabilityResolver,
    ProviderUnavailableError,
)
from app.registry.client import RegistryClient, RegistryMappingError, RegistryUnavailable
from app.registry.discovery import McpDiscoveryError, McpToolDiscovery
from app.registry.dynamic_resolver import DynamicAgentResolver, DynamicResolutionError
from app.solver.problems import PROBLEM_9, PROBLEM_10
from app.validation.guardrail import DeterministicGuardrail, OptimizationState


# 1. MCP Unavailable
def test_safety_mcp_unavailable() -> None:
    def failing_transport(url: str, method: str, body: bytes | None) -> bytes:
        raise ConnectionRefusedError("Connection refused to MCP server port 7101")

    client = RegistryClient("http://registry.local", transport=failing_transport)
    resolver = CapabilityResolver(client)
    with pytest.raises(RegistryUnavailable):
        resolver.resolve_capability("route_optimization")


# 2. Agent Disabled
def test_safety_agent_disabled() -> None:
    agent = AgentDefinition(
        id="disabled-agent",
        version="1.0",
        enabled=False,
        name="Disabled",
        description="",
        capabilities=("route_optimization",),
        instructions="",
        input_contract={},
        output_contract={},
        allowed_tools=(),
        limits=AgentLimits(),
    )
    registry = AgentRegistry((agent,))
    with pytest.raises(AgentDisabledError):
        registry.get("disabled-agent", enabled_only=True)


# 3. Unknown Capability
def test_safety_unknown_capability() -> None:
    def empty_transport(url: str, method: str, body: bytes | None) -> bytes:
        return json.dumps([]).encode()

    client = RegistryClient("http://registry.local", transport=empty_transport)
    resolver = CapabilityResolver(client)
    with pytest.raises(CapabilityNotFoundError) as exc:
        resolver.resolve_capability("quantum_teleportation")
    assert "no enabled tool registered for capability: quantum_teleportation" in str(exc.value)


# 4. Unknown Agent
def test_safety_unknown_agent() -> None:
    registry = AgentRegistry(())
    with pytest.raises(AgentNotFoundError):
        registry.get("phantom_agent")


# 5. Duplicate Registration
def test_safety_duplicate_registration() -> None:
    agent = AgentDefinition(
        id="unique-agent",
        version="1.0",
        enabled=True,
        name="Unique",
        description="",
        capabilities=("route_optimization",),
        instructions="",
        input_contract={},
        output_contract={},
        allowed_tools=(),
        limits=AgentLimits(),
    )
    registry = AgentRegistry((agent,))
    with pytest.raises(RegistryError) as exc:
        registry.register(agent)
    assert "already registered" in str(exc.value)


# 6. Invalid MCP Endpoint
def test_safety_invalid_mcp_endpoint() -> None:
    with pytest.raises(RegistryMappingError):
        from app.registry.client import map_mcp_server
        map_mcp_server({"id": "server-1", "name": "Server", "endpoint": ""})


# 7. Tool Unavailable / Provider Disabled
def test_safety_tool_provider_disabled() -> None:
    def mock_transport(url: str, method: str, body: bytes | None) -> bytes:
        if "/api/v1/tools" in url:
            return json.dumps([
                {
                    "tool_id": "test_tool",
                    "name": "Test Tool",
                    "capability": "route_optimization",
                    "provider": "disabled-mcp",
                    "enabled": True,
                }
            ]).encode()
        if "/api/v1/mcp-servers/disabled-mcp" in url:
            return json.dumps({
                "id": "disabled-mcp",
                "name": "Disabled MCP",
                "endpoint": "http://localhost:7101",
                "enabled": False,
                "version": "1.0",
            }).encode()
        return b"{}"

    client = RegistryClient("http://registry.local", transport=mock_transport)
    resolver = CapabilityResolver(client)
    with pytest.raises(ProviderUnavailableError) as exc:
        resolver.resolve_capability("route_optimization")
    assert "is disabled" in str(exc.value)


# 8. LLM Returns Invalid Capability Format or Infrastructure URL
def test_safety_llm_returns_invalid_capability() -> None:
    analyzer = TaskAnalyzer()
    with pytest.raises(SecurityPolicyViolation):
        analyzer.sanitize_capabilities(["https://evil.corp/exploit"])

    with pytest.raises(InvalidCapabilityError):
        analyzer.sanitize_capabilities(["$$$invalid_chars###"])


# 9. No Agent Capable of Task
def test_safety_no_agent_capable() -> None:
    registry = AgentRegistry(())
    resolver = DynamicAgentResolver(registry, default_agent_factory)
    with pytest.raises(DynamicResolutionError) as exc:
        resolver.resolve_capabilities(("route_optimization",))
    assert "No enabled agent capable of performing" in str(exc.value)


# 10. Conflicting Recommendations Reconciled by Critic / Refiner
def test_safety_conflicting_recommendations() -> None:
    agent_a = AgentDefinition(
        id="agent-a", version="1.0", enabled=True, name="A", description="",
        capabilities=("cap",), instructions="", input_contract={}, output_contract={}, allowed_tools=(), limits=AgentLimits()
    )
    agent_b = AgentDefinition(
        id="agent-b", version="1.0", enabled=True, name="B", description="",
        capabilities=("cap",), instructions="", input_contract={}, output_contract={}, allowed_tools=(), limits=AgentLimits()
    )
    registry = AgentRegistry((agent_a, agent_b))

    from app.registry.resolver import AgentResolver

    resolver = AgentResolver(
        registry,
        lambda d: lambda task: AgentResult(
            agent_id=d.id,
            status="completed",
            recommendation="Route through A" if d.id == "agent-a" else "Route through B (conflict)",
        ),
    )
    orchestrator = Orchestrator(resolver)
    routing = RoutingResult(selected_agents=(SelectedAgent("agent-a", "reason-a", "task-a"), SelectedAgent("agent-b", "reason-b", "task-b")))

    # Critic detects conflict
    def critic(proposal: str) -> Critique:
        if "conflict" in proposal:
            return Critique(valid=False, issue="Conflicting routes proposed", question="Which route is optimal?")
        return Critique(valid=True, issue="", question="")

    def refiner(proposal: str, critique: Critique) -> str:
        # Refiner resolves tie deterministically
        return "Resolved: Route through A (verified lowest cost)"

    result = orchestrator.run_governed(routing, critic=critic, refiner=refiner)
    assert result.status == "completed"
    assert "Resolved: Route through A" in result.final_decision


# 11. Impossible Routing Problem (Disconnected Island) Deterministically Caught
def test_safety_impossible_disconnected_island() -> None:
    guardrail = DeterministicGuardrail(PROBLEM_9)
    result = guardrail.validate_proposal(("A", "B", "C", "D"))
    assert result.is_valid is False
    assert result.state == OptimizationState.IMPOSSIBLE
    assert "disconnected graph" in result.reason


# 12. Circular Dependency Deterministically Caught
def test_safety_circular_dependency() -> None:
    guardrail = DeterministicGuardrail(PROBLEM_10)
    result = guardrail.validate_proposal(("A", "B", "C"))
    assert result.is_valid is False
    assert result.state == OptimizationState.IMPOSSIBLE
    assert "circular dependency detected" in result.reason
