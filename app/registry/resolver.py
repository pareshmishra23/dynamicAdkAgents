from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from app.models import AgentDefinition, AgentResult
from app.registry.agent_registry import AgentRegistry


@dataclass(frozen=True)
class ResolvedAgent:
    definition: AgentDefinition
    execute: Callable[[str], AgentResult]


class AgentResolver:
    """Resolve only registry-approved agents, creating execution adapters on demand."""

    def __init__(self, registry: AgentRegistry, factory: Callable[[AgentDefinition], Callable[[str], AgentResult]]) -> None:
        self.registry = registry
        self.factory = factory

    def resolve(self, agent_id: str) -> ResolvedAgent:
        definition = self.registry.get(agent_id, enabled_only=True)
        return ResolvedAgent(definition=definition, execute=self.factory(definition))
