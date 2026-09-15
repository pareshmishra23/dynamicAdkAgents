from __future__ import annotations

import json
import pytest

from app.analyzer.task_analyzer import TaskAnalyzer
from app.agents.orchestrator import Orchestrator
from app.models import AgentDefinition, AgentLimits, AgentResult, RoutingResult, SelectedAgent
from app.registry.agent_registry import AgentDisabledError
from app.registry.client import RegistryClient
from app.registry.dynamic_resolver import DynamicAgentResolver, DynamicResolutionError


def test_bead_13_dynamic_runtime_interview_demonstration() -> None:
    """Demonstrates live zero-code runtime adaptation:

    1. Start with route-optimizer and constraint-agent in FastAPI registry.
    2. Submit a task requiring graph_analysis -> platform fails/rejects because no agent exists.
    3. Via REST POST /api/v1/agents, register graph-analysis-agent dynamically (ZERO code modification).
    4. Submit the task again -> platform dynamically discovers agent, wraps as Agent-as-Tool, orchestrates successfully.
    5. Via REST PATCH /api/v1/agents/{id}/disable, disable graph-analysis-agent.
    6. Submit the task again -> platform strictly rejects/abstains and DOES NOT use the disabled agent.
    """

    # In-memory mock store representing the live FastAPI Registry Control Plane
    registry_db: dict[str, dict] = {
        "route-optimizer": {
            "id": "route-optimizer",
            "name": "Route Optimizer",
            "description": "Optimizes routes",
            "capabilities": ["route_optimization"],
            "model": "gemini-flash-latest",
            "enabled": True,
        },
        "constraint-agent": {
            "id": "constraint-agent",
            "name": "Constraint Agent",
            "description": "Evaluates topological constraints",
            "capabilities": ["constraint_reasoning"],
            "model": "gemini-flash-latest",
            "enabled": True,
        },
    }

    def mock_transport(url: str, method: str, body: bytes | None) -> bytes:
        if "/api/v1/agents?enabled=true" in url and method == "GET":
            enabled = [v for v in registry_db.values() if v.get("enabled")]
            return json.dumps(enabled).encode()

        if "/api/v1/agents" in url and method == "POST" and body:
            payload = json.loads(body.decode())
            payload["enabled"] = True
            registry_db[payload["id"]] = payload
            return json.dumps(payload).encode()

        for agent_id in list(registry_db.keys()):
            if f"/api/v1/agents/{agent_id}/disable" in url and method == "PATCH":
                registry_db[agent_id]["enabled"] = False
                return json.dumps(registry_db[agent_id]).encode()

            if f"/api/v1/agents/{agent_id}" in url and method == "GET":
                return json.dumps(registry_db[agent_id]).encode()

        return b"{}"

    client = RegistryClient("http://registry.controlplane", transport=mock_transport)
    analyzer = TaskAnalyzer()

    # Step 1: Baseline agents present
    baseline_agents = client.fetch_enabled_agents()
    assert {a.id for a in baseline_agents} == {"route-optimizer", "constraint-agent"}

    # Dynamic factory that creates working agent implementations
    executed_agents: list[str] = []

    def runtime_factory(definition: AgentDefinition):
        def _exec(task: str) -> AgentResult:
            executed_agents.append(definition.id)
            return AgentResult(
                agent_id=definition.id,
                status="completed",
                recommendation=f"Executed by {definition.id} for task: {task}",
            )
        return _exec

    resolver = DynamicAgentResolver(client, runtime_factory)

    # Step 2: Task requiring graph_analysis submitted
    user_task = "Analyze the distance graph connectivity and find islands."
    intent = analyzer.analyze(user_task)
    assert "graph_analysis" in intent.capabilities

    # Fails dynamically because graph_analysis agent is not yet registered
    with pytest.raises(DynamicResolutionError) as exc_info:
        resolver.resolve_capabilities(intent.capabilities, task_context=user_task)
    assert "No enabled agent capable of performing: graph_analysis" in str(exc_info.value)

    # Step 3: Register graph-analysis-agent through REST API (Zero application code change!)
    new_agent_payload = {
        "id": "graph-analysis-agent",
        "name": "Graph Analysis Agent",
        "description": "Inspects topological connectivity and builds distance matrices",
        "capabilities": ["graph_analysis"],
        "model": "gemini-flash-latest",
        "enabled": True,
    }
    registered_agent = client.register_agent(new_agent_payload)
    assert registered_agent.id == "graph-analysis-agent"
    assert "graph_analysis" in registered_agent.capabilities

    # Step 4: Submit the problem again -> dynamically discovers new agent, wraps as tool, orchestrates!
    pool = resolver.resolve_capabilities(intent.capabilities, task_context=user_task)
    assert any(a.id == "graph-analysis-agent" for a in pool.agents)
    assert any(t.agent_id == "graph-analysis-agent" for t in pool.tools)

    # Orchestrator receives ONLY the scoped tools required
    from app.registry.agent_registry import AgentRegistry
    from app.registry.resolver import AgentResolver

    temp_reg = AgentRegistry(pool.agents)
    orch_resolver = AgentResolver(temp_reg, runtime_factory)
    orchestrator = Orchestrator(orch_resolver)

    result = orchestrator.run(pool.routing)
    assert result.status == "completed"
    assert "graph-analysis-agent" in executed_agents
    assert "graph-analysis-agent" in result.final_decision

    # Step 5: Disable the agent via REST PATCH /api/v1/agents/{id}/disable
    disabled_resp = client.disable_agent("graph-analysis-agent")
    assert disabled_resp.enabled is False

    # Step 6: Submit same task again -> platform strictly rejects / does NOT use the disabled agent
    executed_agents.clear()
    with pytest.raises(DynamicResolutionError) as exc_disabled:
        resolver.resolve_capabilities(intent.capabilities, task_context=user_task)
    assert "No enabled agent capable of performing: graph_analysis" in str(exc_disabled.value)
    assert "graph-analysis-agent" not in executed_agents
