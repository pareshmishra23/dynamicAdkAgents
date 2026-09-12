from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class AgentLimits:
    timeout_seconds: int = 60
    max_tool_calls: int = 5


@dataclass(frozen=True)
class AgentDefinition:
    id: str
    version: str
    enabled: bool
    name: str
    description: str
    capabilities: tuple[str, ...]
    instructions: str
    input_contract: dict[str, Any]
    output_contract: dict[str, Any]
    allowed_tools: tuple[str, ...] = ()
    limits: AgentLimits = field(default_factory=AgentLimits)
    model: str = ""
    requires_human_approval: bool = False
    policy: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SelectedAgent:
    agent_id: str
    reason: str
    task: str


@dataclass(frozen=True)
class RoutingResult:
    selected_agents: tuple[SelectedAgent, ...]


@dataclass(frozen=True)
class AgentResult:
    agent_id: str
    status: str
    recommendation: str
    evidence: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    handler: Callable[..., Any]
    allowed_agent_ids: tuple[str, ...] = ()
