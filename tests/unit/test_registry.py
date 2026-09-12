from pathlib import Path

import pytest

from app.config.loader import ConfigurationError, load_agent_definitions, load_llm_config
from app.registry.agent_registry import AgentDisabledError, AgentNotFoundError, AgentRegistry

ROOT = Path(__file__).parents[2]


def test_loads_externalized_configuration():
    llm = load_llm_config(ROOT / "config/llm.yaml")
    definitions = load_agent_definitions(ROOT / "config/agents.yaml")
    assert llm["model"] == "gemini-flash-latest"
    assert {agent.id for agent in definitions} == {
        "sightseeing_agent",
        "adventure_agent",
        "car_rental_agent",
        "taxi_agent",
        "friend_relative_agent",
    }


def test_registry_resolves_by_capability():
    registry = AgentRegistry(load_agent_definitions(ROOT / "config/agents.yaml"))
    matches = registry.find_by_capability("taxi")
    assert [agent.id for agent in matches] == ["taxi_agent"]


def test_registry_rejects_unknown_agent():
    registry = AgentRegistry(load_agent_definitions(ROOT / "config/agents.yaml"))
    with pytest.raises(AgentNotFoundError):
        registry.get("not_registered")


def test_registry_rejects_disabled_agent():
    definitions = list(load_agent_definitions(ROOT / "config/agents.yaml"))
    disabled = definitions[0]
    definitions[0] = disabled.__class__(**{**disabled.__dict__, "enabled": False})
    registry = AgentRegistry(tuple(definitions))
    with pytest.raises(AgentDisabledError):
        registry.get(disabled.id)


def test_invalid_config_is_rejected(tmp_path):
    config = tmp_path / "bad.yaml"
    config.write_text("agents:\n  - id: duplicate\n    version: '1'\n", encoding="utf-8")
    with pytest.raises(ConfigurationError):
        load_agent_definitions(config)
