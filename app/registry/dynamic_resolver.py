from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from app.agents.factory import AgentAsTool
from app.models import AgentDefinition, AgentResult, RoutingResult, SelectedAgent
from app.registry.agent_registry import AgentDisabledError, AgentNotFoundError, AgentRegistry
from app.registry.client import RegistryClient


class DynamicResolutionError(RuntimeError):
    pass


class AgentAuthorizationError(DynamicResolutionError):
    pass


class IncompatibleAgentError(DynamicResolutionError):
    pass


@dataclass(frozen=True)
class ScopedAgentPool:
    agents: tuple[AgentDefinition, ...]
    tools: tuple[AgentAsTool, ...]
    routing: RoutingResult


class DynamicAgentResolver:
    """Resolves task capabilities to authorized, enabled agents and wraps them dynamically as tools.

    Flow:
    Capabilities -> Agent Registry -> enabled? -> authorized? -> compatible? -> Agent-as-a-Tool -> Scoped Pool
    """

    def __init__(
        self,
        registry: AgentRegistry | RegistryClient,
        factory: Callable[[AgentDefinition], Callable[[str], AgentResult]],
        authorized_capabilities: set[str] | None = None,
    ) -> None:
        self.registry = registry
        self.factory = factory
        self.authorized_capabilities = authorized_capabilities

    def _get_agent(self, agent_id: str) -> AgentDefinition:
        if isinstance(self.registry, AgentRegistry):
            return self.registry.get(agent_id, enabled_only=False)
        return self.registry.fetch_agent(agent_id)

    def _list_enabled_agents(self) -> tuple[AgentDefinition, ...]:
        if isinstance(self.registry, AgentRegistry):
            return self.registry.list_enabled()
        return self.registry.fetch_enabled_agents()

    def resolve_agent(self, agent_id: str, required_capability: str | None = None) -> AgentDefinition:
        """Resolve a specific agent by ID with strict security and authorization checks."""
        try:
            definition = self._get_agent(agent_id)
        except Exception as exc:
            raise AgentNotFoundError(f"Unknown agent rejected: {agent_id}") from exc

        # Check 1: Enabled check
        if not definition.enabled:
            raise AgentDisabledError(f"Disabled agent rejected: {agent_id}")

        # Check 2: Capability authorization check
        if self.authorized_capabilities is not None:
            for cap in definition.capabilities:
                if cap not in self.authorized_capabilities:
                    raise AgentAuthorizationError(
                        f"Agent {agent_id} has unauthorized capability: {cap}"
                    )

        # Check 3: Compatibility check if capability specified
        if required_capability:
            normalized_req = required_capability.strip().lower()
            agent_caps = {c.strip().lower() for c in definition.capabilities}
            if normalized_req not in agent_caps:
                raise IncompatibleAgentError(
                    f"Agent {agent_id} does not provide required capability {required_capability}"
                )

        return definition

    def resolve_capabilities(
        self,
        capabilities: tuple[str, ...],
        task_context: str = "",
    ) -> ScopedAgentPool:
        """Dynamically select only the agents needed for the requested capabilities."""
        enabled_agents = self._list_enabled_agents()
        selected_definitions: list[AgentDefinition] = []
        selected_agents_meta: list[SelectedAgent] = []
        tools: list[AgentAsTool] = []
        seen_agent_ids: set[str] = set()

        for capability in capabilities:
            normalized_cap = capability.strip().lower()
            matching = [
                agent
                for agent in enabled_agents
                if normalized_cap in {c.strip().lower() for c in agent.capabilities}
            ]

            if not matching:
                raise DynamicResolutionError(
                    f"No enabled agent capable of performing: {capability}"
                )

            for agent in matching:
                if agent.id not in seen_agent_ids:
                    # Validate agent authorization & compatibility
                    validated = self.resolve_agent(agent.id, required_capability=normalized_cap)
                    seen_agent_ids.add(validated.id)
                    selected_definitions.append(validated)

                    # Dynamic Agent-as-a-Tool creation
                    executor = self.factory(validated)
                    tool = AgentAsTool(validated.id, executor)
                    tools.append(tool)

                    selected_agents_meta.append(
                        SelectedAgent(
                            agent_id=validated.id,
                            reason=f"Selected dynamically for capability: {capability}",
                            task=task_context or f"Execute {capability} for {task_context}",
                        )
                    )

        routing = RoutingResult(selected_agents=tuple(selected_agents_meta))
        return ScopedAgentPool(
            agents=tuple(selected_definitions),
            tools=tuple(tools),
            routing=routing,
        )
