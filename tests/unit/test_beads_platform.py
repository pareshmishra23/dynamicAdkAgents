from __future__ import annotations

import pytest

from app.analyzer.task_analyzer import (
    SecurityPolicyViolation,
    TaskAnalyzer,
)
from app.agents.factory import default_agent_factory
from app.agents.orchestrator import Critique, Orchestrator
from app.models import AgentDefinition, AgentLimits, AgentResult, RoutingResult, SelectedAgent
from app.registry.agent_registry import AgentDisabledError, AgentNotFoundError, AgentRegistry
from app.registry.capability import (
    CapabilityNotFoundError,
    CapabilityResolver,
    ProviderUnavailableError,
)
from app.registry.client import McpServerConfig, RegistryClient, ToolRegistration
from app.registry.discovery import McpToolDiscovery
from app.registry.dynamic_resolver import (
    AgentAuthorizationError,
    DynamicAgentResolver,
    DynamicResolutionError,
)
from app.solver.problems import (
    PROBLEM_1,
    PROBLEM_2,
    PROBLEM_3,
    PROBLEM_4,
    PROBLEM_5,
    PROBLEM_6,
    PROBLEM_7,
    PROBLEM_8,
    PROBLEM_9,
    PROBLEM_10,
)
from app.validation.guardrail import DeterministicGuardrail, OptimizationState


# --------------------------------------------------------------------------
# BEAD 03 & BEAD 04: Authoritative Dynamic Registries (No static AGENTS dict)
# --------------------------------------------------------------------------
def test_dynamic_registry_client_mock_transport() -> None:
    store: dict[str, dict] = {
        "/api/v1/agents?enabled=true": {
            "items": [
                {
                    "id": "route-optimizer",
                    "name": "Route Optimizer",
                    "description": "Optimizes constrained routes",
                    "capabilities": ["route_optimization", "constraint_reasoning"],
                    "enabled": True,
                    "model": "gemini-flash-latest",
                    "policy": {"timeout_seconds": 30, "max_tool_calls": 10},
                }
            ]
        },
        "/api/v1/mcp-servers?enabled=true": {
            "items": [
                {
                    "id": "solver-mcp",
                    "name": "Solver MCP",
                    "endpoint": "http://localhost:7101",
                    "transport": "http",
                    "enabled": True,
                    "version": "1.0",
                }
            ]
        },
    }

    import json

    def mock_transport(url: str, method: str, body: bytes | None) -> bytes:
        for path, data in store.items():
            if url.endswith(path):
                return json.dumps(data).encode()
        return b"{}"

    client = RegistryClient("http://registry.local", transport=mock_transport)

    agents = client.fetch_enabled_agents()
    assert len(agents) == 1
    assert agents[0].id == "route-optimizer"
    assert "route_optimization" in agents[0].capabilities
    assert agents[0].model == "gemini-flash-latest"

    servers = client.fetch_enabled_mcp_servers()
    assert len(servers) == 1
    assert servers[0].id == "solver-mcp"
    assert servers[0].endpoint == "http://localhost:7101"


# --------------------------------------------------------------------------
# BEAD 05: Dynamic Tool Discovery (MCP -> Discovery -> Tool Registry)
# --------------------------------------------------------------------------
def test_dynamic_tool_discovery_from_mcp() -> None:
    tool_registry_db: dict[str, dict] = {}

    import json

    def mock_transport(url: str, method: str, body: bytes | None) -> bytes:
        if method == "POST" and "/api/v1/tools" in url and body:
            data = json.loads(body.decode())
            tool_registry_db[data["tool_id"]] = data
            return body
        return b"{}"

    client = RegistryClient("http://registry.local", transport=mock_transport)

    def mock_mcp_caller(server: McpServerConfig, action: str):
        return {
            "tools": [
                {
                    "tool_id": "route_solver_tool",
                    "name": "Route Solver Tool",
                    "description": "Calculates shortest TSP cycle",
                    "capability": "route_optimization",
                },
                {
                    "tool_id": "constraint_checker_tool",
                    "name": "Constraint Checker Tool",
                    "description": "Validates ordering constraints",
                    "capability": "constraint_reasoning",
                },
            ]
        }

    discovery = McpToolDiscovery(client, mcp_caller=mock_mcp_caller)
    server = McpServerConfig(
        id="solver-mcp",
        name="Solver MCP",
        description="",
        endpoint="http://localhost:7101",
        transport="http",
        enabled=True,
        version="1.0",
    )

    discovered = discovery.discover_and_register(server)
    assert len(discovered) == 2
    assert {t.tool_id for t in discovered} == {"route_solver_tool", "constraint_checker_tool"}
    assert {t.capability for t in discovered} == {"route_optimization", "constraint_reasoning"}
    assert all(t.provider == "solver-mcp" for t in discovered)
    assert len(tool_registry_db) == 2


# --------------------------------------------------------------------------
# BEAD 06: Capability Resolver & Provider Independence
# --------------------------------------------------------------------------
def test_capability_resolver_provider_independence() -> None:
    # Today: route_optimization -> Solver MCP
    # Tomorrow: route_optimization -> Gurobi service (without changing agent!)
    import json

    current_provider = "solver-mcp"

    def mock_transport(url: str, method: str, body: bytes | None) -> bytes:
        if "/api/v1/tools" in url:
            return json.dumps([
                {
                    "tool_id": "optimizer_tool",
                    "name": "Optimizer Tool",
                    "description": "Optimizes routes",
                    "capability": "route_optimization",
                    "provider": current_provider,
                    "enabled": True,
                }
            ]).encode()
        if f"/api/v1/mcp-servers/{current_provider}" in url:
            endpoint = "http://localhost:7101" if current_provider == "solver-mcp" else "https://gurobi.corp.internal"
            return json.dumps({
                "id": current_provider,
                "name": current_provider,
                "endpoint": endpoint,
                "transport": "http",
                "enabled": True,
                "version": "1.0",
            }).encode()
        return b"{}"

    client = RegistryClient("http://registry.local", transport=mock_transport)
    resolver = CapabilityResolver(client)

    # Resolve with today's provider
    resolved_today = resolver.resolve_capability("route_optimization")
    assert resolved_today.provider_id == "solver-mcp"
    assert resolved_today.endpoint == "http://localhost:7101"

    # Swap to Gurobi service tomorrow without modifying agent
    current_provider = "gurobi-service"
    resolved_tomorrow = resolver.resolve_capability("route_optimization")
    assert resolved_tomorrow.provider_id == "gurobi-service"
    assert resolved_tomorrow.endpoint == "https://gurobi.corp.internal"


# --------------------------------------------------------------------------
# BEAD 07: Dynamic LLM Task Analyzer & Security Boundary
# --------------------------------------------------------------------------
def test_task_analyzer_security_rejects_infrastructure_injection() -> None:
    analyzer = TaskAnalyzer()

    # Normal intent extraction
    intent = analyzer.analyze("Solve this 15-city routing problem with constraints.")
    assert "route_optimization" in intent.capabilities
    assert "constraint_reasoning" in intent.capabilities

    # Security violation: LLM tries to directly select a URL or database
    with pytest.raises(SecurityPolicyViolation):
        analyzer.sanitize_capabilities(["route_optimization", "http://malicious-endpoint.local/exec"])

    with pytest.raises(SecurityPolicyViolation):
        analyzer.sanitize_capabilities(["route_optimization", "SELECT * FROM users"])

    with pytest.raises(SecurityPolicyViolation):
        analyzer.sanitize_capabilities(["jdbc:h2:mem:adk"])


# --------------------------------------------------------------------------
# BEAD 08 & BEAD 09: Dynamic Agent Resolver & Scoped Agent-as-a-Tool
# --------------------------------------------------------------------------
def test_dynamic_agent_resolver_and_agent_as_tool() -> None:
    agent_1 = AgentDefinition(
        id="route-optimizer",
        version="1.0",
        enabled=True,
        name="Route Optimizer",
        description="Optimizes routes",
        capabilities=("route_optimization",),
        instructions="",
        input_contract={},
        output_contract={},
        allowed_tools=(),
        limits=AgentLimits(),
    )
    agent_disabled = AgentDefinition(
        id="disabled-agent",
        version="1.0",
        enabled=False,
        name="Disabled Agent",
        description="",
        capabilities=("graph_analysis",),
        instructions="",
        input_contract={},
        output_contract={},
        allowed_tools=(),
        limits=AgentLimits(),
    )

    registry = AgentRegistry((agent_1, agent_disabled))

    def dummy_factory(definition: AgentDefinition):
        return lambda task: AgentResult(agent_id=definition.id, status="completed", recommendation=f"Result for {task}")

    resolver = DynamicAgentResolver(registry, dummy_factory, authorized_capabilities={"route_optimization", "graph_analysis"})

    # Resolving required capabilities loads ONLY the matching agents
    pool = resolver.resolve_capabilities(("route_optimization",), task_context="Solve TSP")
    assert len(pool.agents) == 1
    assert pool.agents[0].id == "route-optimizer"
    assert len(pool.tools) == 1
    assert pool.tools[0].agent_id == "route-optimizer"

    # Tool execution works
    tool_result = pool.tools[0]("test task")
    assert tool_result.recommendation == "Result for test task"

    # Reject disabled agent
    with pytest.raises(AgentDisabledError):
        resolver.resolve_agent("disabled-agent")

    # Reject unknown agent
    with pytest.raises(AgentNotFoundError):
        resolver.resolve_agent("non-existent-agent")

    # Reject unknown capability
    with pytest.raises(DynamicResolutionError):
        resolver.resolve_capabilities(("unknown_capability",))


# --------------------------------------------------------------------------
# BEAD 10: Single Decision Owner & Governed Orchestrator
# --------------------------------------------------------------------------
def test_single_decision_owner_pipeline() -> None:
    agent_def = AgentDefinition(
        id="specialist-1",
        version="1.0",
        enabled=True,
        name="Specialist",
        description="",
        capabilities=("testing",),
        instructions="",
        input_contract={},
        output_contract={},
        allowed_tools=(),
        limits=AgentLimits(),
    )
    registry = AgentRegistry((agent_def,))
    from app.registry.resolver import AgentResolver

    resolver = AgentResolver(
        registry,
        lambda d: lambda task: AgentResult(agent_id=d.id, status="completed", recommendation="Initial recommendation with 4 days"),
    )
    orchestrator = Orchestrator(resolver)
    routing = RoutingResult(selected_agents=(SelectedAgent("specialist-1", "test", "task"),))

    # Single decision owner pipeline: Specialist -> Critic -> Refiner -> Decision
    def critic(proposal: str) -> Critique:
        if "4 days" in proposal:
            return Critique(valid=False, issue="Exceeds 3 day maximum", question="Shorten to 3 days?")
        return Critique(valid=True, issue="", question="")

    def refiner(proposal: str, critique: Critique) -> str:
        return proposal.replace("4 days", "3 days")

    result = orchestrator.run_governed(routing, critic=critic, refiner=refiner)
    assert result.status == "completed"
    assert "3 days" in result.final_decision
    assert result.trace[-1] == "orchestrator"
    assert "specialist_recommendations" in result.trace
    assert "critic" in result.trace
    assert "refiner" in result.trace


# --------------------------------------------------------------------------
# BEAD 11 & BEAD 12: Deterministic Guardrail & Optimization States on 10 Benchmark Problems
# --------------------------------------------------------------------------
def test_deterministic_guardrail_distinct_states() -> None:
    # 1. Triangle (P1) -> OPTIMAL
    g1 = DeterministicGuardrail(PROBLEM_1)
    v1 = g1.validate_proposal(PROBLEM_1.expected)
    assert v1.is_valid is True
    assert v1.state == OptimizationState.OPTIMAL

    # 2. Square (P2) -> OPTIMAL
    g2 = DeterministicGuardrail(PROBLEM_2)
    v2 = g2.validate_proposal(PROBLEM_2.expected)
    assert v2.is_valid is True
    assert v2.state == OptimizationState.OPTIMAL

    # 3. Linear Highway (P3) -> OPTIMAL
    g3 = DeterministicGuardrail(PROBLEM_3)
    v3 = g3.validate_proposal(PROBLEM_3.expected)
    assert v3.is_valid is True
    assert v3.state == OptimizationState.OPTIMAL

    # 4. Asymmetric One-Way (P4) -> OPTIMAL
    g4 = DeterministicGuardrail(PROBLEM_4)
    v4 = g4.validate_proposal(PROBLEM_4.expected)
    assert v4.is_valid is True
    assert v4.state == OptimizationState.OPTIMAL

    # 5. Morning Hub Constraint (P5) -> OPTIMAL
    g5 = DeterministicGuardrail(PROBLEM_5)
    v5 = g5.validate_proposal(PROBLEM_5.expected)
    assert v5.is_valid is True
    assert v5.state == OptimizationState.OPTIMAL

    # 6. Hub-and-Spoke (P6) -> OPTIMAL
    g6 = DeterministicGuardrail(PROBLEM_6)
    v6 = g6.validate_proposal(PROBLEM_6.expected)
    assert v6.is_valid is True
    assert v6.state == OptimizationState.OPTIMAL

    # 7. 15-City Factorial (P7) -> FEASIBLE but UNPROVEN (Mandate: FEASIBLE != OPTIMAL)
    g7 = DeterministicGuardrail(PROBLEM_7)
    v7 = g7.validate_proposal(PROBLEM_7.cities, is_heuristic=True)
    assert v7.is_valid is True
    assert v7.state == OptimizationState.UNPROVEN
    assert "optimality is UNPROVEN" in v7.reason

    # 8. VRP Split (P8) -> FEASIBLE but UNPROVEN
    g8 = DeterministicGuardrail(PROBLEM_8)
    subroute_a = ("c1", "c2", "c3", "c4")
    subroute_b = ("c5", "c6", "c7", "c8", "c9")
    v8 = g8.validate_proposal(vrp_routes=(subroute_a, subroute_b), is_heuristic=True)
    assert v8.is_valid is True
    assert v8.state == OptimizationState.UNPROVEN

    # 9. Disconnected Island (P9) -> IMPOSSIBLE (Abstain, zero hallucination)
    g9 = DeterministicGuardrail(PROBLEM_9)
    v9 = g9.validate_proposal(("A", "B", "C", "D"))
    assert v9.is_valid is False
    assert v9.state == OptimizationState.IMPOSSIBLE
    assert "disconnected graph" in v9.reason

    # 10. Time-Paradox / Circular Dependency (P10) -> IMPOSSIBLE
    g10 = DeterministicGuardrail(PROBLEM_10)
    v10 = g10.validate_proposal(("A", "B", "C"))
    assert v10.is_valid is False
    assert v10.state == OptimizationState.IMPOSSIBLE
    assert "circular dependency detected" in v10.reason
