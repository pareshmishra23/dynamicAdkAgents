from __future__ import annotations

from app.models import AgentDefinition


class RegistryError(ValueError):
    pass


class AgentNotFoundError(RegistryError):
    pass


class AgentDisabledError(RegistryError):
    pass


class AgentRegistry:
    def __init__(self, definitions: tuple[AgentDefinition, ...] = ()) -> None:
        self._agents: dict[str, AgentDefinition] = {}
        for definition in definitions:
            self.register(definition)

    def register(self, definition: AgentDefinition) -> None:
        if definition.id in self._agents:
            raise RegistryError(f"agent already registered: {definition.id}")
        self._agents[definition.id] = definition

    def remove(self, agent_id: str) -> None:
        if agent_id not in self._agents:
            raise AgentNotFoundError(f"unknown agent: {agent_id}")
        del self._agents[agent_id]

    def enable(self, agent_id: str) -> None:
        self._set_enabled(agent_id, True)

    def disable(self, agent_id: str) -> None:
        self._set_enabled(agent_id, False)

    def _set_enabled(self, agent_id: str, enabled: bool) -> None:
        definition = self._agents.get(agent_id)
        if definition is None:
            raise AgentNotFoundError(f"unknown agent: {agent_id}")
        self._agents[agent_id] = AgentDefinition(
            id=definition.id,
            version=definition.version,
            enabled=enabled,
            name=definition.name,
            description=definition.description,
            capabilities=definition.capabilities,
            instructions=definition.instructions,
            input_contract=definition.input_contract,
            output_contract=definition.output_contract,
            allowed_tools=definition.allowed_tools,
            limits=definition.limits,
            model=definition.model,
            requires_human_approval=definition.requires_human_approval,
            policy=definition.policy,
        )

    def get(self, agent_id: str, *, enabled_only: bool = True) -> AgentDefinition:
        definition = self._agents.get(agent_id)
        if definition is None:
            raise AgentNotFoundError(f"unknown agent: {agent_id}")
        if enabled_only and not definition.enabled:
            raise AgentDisabledError(f"agent is disabled: {agent_id}")
        return definition

    def list_enabled(self) -> tuple[AgentDefinition, ...]:
        return tuple(agent for agent in self._agents.values() if agent.enabled)

    def find_by_capability(self, capability: str) -> tuple[AgentDefinition, ...]:
        normalized = capability.strip().lower()
        return tuple(
            agent for agent in self.list_enabled() if normalized in {item.lower() for item in agent.capabilities}
        )

    def contains(self, agent_id: str, *, enabled_only: bool = False) -> bool:
        try:
            self.get(agent_id, enabled_only=enabled_only)
        except RegistryError:
            return False
        return True

    def metadata(self) -> tuple[dict[str, object], ...]:
        return tuple(
            {
                "id": agent.id,
                "version": agent.version,
                "name": agent.name,
                "description": agent.description,
                "capabilities": agent.capabilities,
                "enabled": agent.enabled,
            }
            for agent in self._agents.values()
        )
