from pathlib import Path

import pytest

from app.agents.adk_adapter import ADKUnavailableError, build_adk_agent
from app.config.loader import load_agent_definitions

ROOT = Path(__file__).parents[2]


def test_real_adk_adapter_is_optional_without_dependency():
    definition = load_agent_definitions(ROOT / "config/agents.yaml")[0]
    try:
        agent = build_adk_agent(definition, model="gemini-flash-latest")
    except ADKUnavailableError:
        pytest.skip("optional google-adk package is not installed")
    assert agent.name == definition.id
    assert agent.model == "gemini-flash-latest"
