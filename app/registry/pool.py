from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from app.models import AgentDefinition
from app.registry.agent_registry import AgentRegistry, RegistryError
from app.registry.client import RegistryClient


@dataclass(frozen=True)
class PoolRefreshReport:
    added: tuple[str, ...]
    disabled: tuple[str, ...]
    version_changed: tuple[str, ...]
    total_enabled: int

    @property
    def changed(self) -> bool:
        return bool(self.added or self.disabled or self.version_changed)


@dataclass
class RuntimePoolState:
    active_version: str
    previous_version: str | None = None


class DynamicPool:
    """In-memory agent pool whose membership is driven by the registry control plane."""

    def __init__(
        self,
        registry: AgentRegistry,
        client: RegistryClient | None = None,
        notify: Callable[[str], None] | None = None,
    ) -> None:
        self.registry = registry
        self.client = client
        self._notify = notify or (lambda message: None)
        self._versions: dict[str, RuntimePoolState] = {}

    def _snapshot(self) -> dict[str, AgentDefinition]:
        try:
            return {agent.id: agent for agent in self.registry.list_enabled()}
        except RegistryError:
            return {}

    def refresh(self) -> PoolRefreshReport:
        if self.client is None:
            raise RegistryError("dynamic pool has no registry client to refresh from")
        fetched = self.client.fetch_enabled_agents()
        current = {definition.id: definition for definition in fetched}
        existing = self._snapshot()

        added: list[str] = []
        disabled: list[str] = []
        version_changed: list[str] = []
        for agent_id, definition in current.items():
            old = existing.get(agent_id)
            if old is None:
                self.registry.register(definition)
                added.append(agent_id)
                self._versions[agent_id] = RuntimePoolState(active_version=definition.version)
                self._notify(f"pool {agent_id} registered at v{definition.version}")
            elif old.version != definition.version:
                rollback_candidate = RuntimePoolState(active_version=old.version, previous_version=old.version)
                self._versions[agent_id] = rollback_candidate
                self._registry_replace(old, definition)
                version_changed.append(agent_id)
                self._notify(f"pool {agent_id} updated {old.version} -> {definition.version}")

        for agent_id, old in existing.items():
            if agent_id in current:
                continue
            if agent_id not in self._versions:
                self._versions[agent_id] = RuntimePoolState(active_version=old.version)
            self.registry.disable(agent_id)
            disabled.append(agent_id)
            self._notify(f"pool {agent_id} disabled (no longer in registry)")

        return PoolRefreshReport(
            added=tuple(added),
            disabled=tuple(disabled),
            version_changed=tuple(version_changed),
            total_enabled=len(current),
        )

    def _registry_replace(self, old: AgentDefinition, new: AgentDefinition) -> None:
        self.registry.remove(old.id)
        self.registry.register(new)

    def enable(self, agent_id: str) -> None:
        if self.client is not None:
            self.client.enable_agent(agent_id)
        self.registry.enable(agent_id)
        self._notify(f"pool {agent_id} enabled")

    def disable(self, agent_id: str) -> None:
        if self.client is not None:
            self.client.disable_agent(agent_id)
        self.registry.disable(agent_id)
        self._notify(f"pool {agent_id} disabled")

    def rollback_version(self, agent_id: str, definition: AgentDefinition) -> None:
        old = self.registry.get(agent_id, enabled_only=False)
        state = self._versions.setdefault(
            agent_id, RuntimePoolState(active_version=old.version, previous_version=None)
        )
        if state.previous_version is None:
            state.previous_version = state.active_version
        state.active_version = definition.version
        self._registry_replace(old, definition)
        self._notify(f"pool {agent_id} rolled back to v{definition.version}")
        if self.client is not None:
            self.client.update_agent(agent_id, self._definition_to_payload(definition))

    def _definition_to_payload(self, definition: AgentDefinition) -> dict:
        return {
            "id": definition.id,
            "name": definition.name,
            "description": definition.description,
            "capability": definition.capabilities[0] if definition.capabilities else "",
            "model": definition.model,
            "enabled": definition.enabled,
            "version": definition.version,
            "config": {"allowed_tools": list(definition.allowed_tools)},
            "policy": {
                "timeout_seconds": definition.limits.timeout_seconds,
                "max_tool_calls": definition.limits.max_tool_calls,
                **definition.policy,
            },
            "output_contract": definition.output_contract,
            "requires_human_approval": definition.requires_human_approval,
        }