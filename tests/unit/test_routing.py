from pathlib import Path

import pytest

from app.agents.factory import AgentAsTool, default_agent_factory
from app.agents.router import Router, RoutingError
from app.config.loader import load_agent_definitions
from app.registry.agent_registry import AgentRegistry
from app.registry.resolver import AgentResolver

ROOT = Path(__file__).parents[2]


def registry():
    return AgentRegistry(load_agent_definitions(ROOT / "config/agents.yaml"))


def test_router_selects_matching_capabilities_dynamically():
    result = Router(registry()).route("I need sightseeing, adventure and taxis")
    assert {item.agent_id for item in result.selected_agents} == {
        "sightseeing_agent",
        "adventure_agent",
        "taxi_agent",
    }


def test_router_rejects_unknown_selected_agent():
    with pytest.raises(RoutingError, match="unknown agent"):
        Router(registry()).route("request", selected_agent_ids=["banking_magic_agent"])


def test_resolver_creates_agent_on_demand_as_tool():
    resolved = AgentResolver(registry(), default_agent_factory).resolve("taxi_agent")
    tool = AgentAsTool(resolved.definition.id, resolved.execute)
    result = tool("office to home commute")
    assert tool.name == "taxi_agent_tool"
    assert result.agent_id == "taxi_agent"
    assert result.status == "completed"


def test_agent_tool_rejects_empty_task():
    resolved = AgentResolver(registry(), default_agent_factory).resolve("taxi_agent")
    with pytest.raises(ValueError):
        AgentAsTool("taxi_agent", resolved.execute)("")
