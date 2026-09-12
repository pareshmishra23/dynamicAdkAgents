from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.models import AgentDefinition, AgentLimits


class ConfigurationError(ValueError):
    pass


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigurationError(f"Configuration file does not exist: {path}")
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ConfigurationError(f"Configuration root must be a mapping: {path}")
    return data


def load_llm_config(path: str | Path) -> dict[str, Any]:
    data = _read_yaml(Path(path))
    llm = data.get("llm")
    if not isinstance(llm, dict) or not llm.get("model"):
        raise ConfigurationError("llm.model is required")
    return llm


def load_agent_definitions(path: str | Path) -> tuple[AgentDefinition, ...]:
    data = _read_yaml(Path(path))
    entries = data.get("agents")
    if not isinstance(entries, list):
        raise ConfigurationError("agents must be a list")

    definitions: list[AgentDefinition] = []
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ConfigurationError("each agent must be a mapping")
        required = ("id", "version", "name", "description", "capabilities", "instructions")
        missing = [key for key in required if not entry.get(key)]
        if missing:
            raise ConfigurationError(f"agent is missing required fields: {missing}")
        agent_id = str(entry["id"])
        if agent_id in seen:
            raise ConfigurationError(f"duplicate agent id: {agent_id}")
        seen.add(agent_id)
        if not agent_id.replace("_", "").replace("-", "").isalnum():
            raise ConfigurationError(f"invalid agent id: {agent_id}")
        limits_data = entry.get("limits") or {}
        limits = AgentLimits(
            timeout_seconds=int(limits_data.get("timeout_seconds", 60)),
            max_tool_calls=int(limits_data.get("max_tool_calls", 5)),
        )
        if limits.timeout_seconds <= 0 or limits.max_tool_calls < 0:
            raise ConfigurationError(f"invalid limits for agent: {agent_id}")
        policy_data = entry.get("policy")
        if policy_data is not None and not isinstance(policy_data, dict):
            raise ConfigurationError(f"policy must be a mapping for agent: {agent_id}")
        definitions.append(
            AgentDefinition(
                id=agent_id,
                version=str(entry["version"]),
                enabled=bool(entry.get("enabled", True)),
                name=str(entry["name"]),
                description=str(entry["description"]),
                capabilities=tuple(str(item) for item in entry["capabilities"]),
                instructions=str(entry["instructions"]),
                input_contract=dict(entry.get("input_contract") or {}),
                output_contract=dict(entry.get("output_contract") or {}),
                allowed_tools=tuple(str(item) for item in entry.get("allowed_tools") or []),
                limits=limits,
                model=str(entry.get("model") or ""),
                requires_human_approval=bool(entry.get("requires_human_approval", False)),
                policy=dict(policy_data or {}),
            )
        )
    return tuple(definitions)
