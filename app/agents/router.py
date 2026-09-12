from __future__ import annotations

import re

from app.models import RoutingResult, SelectedAgent
from app.registry.agent_registry import AgentRegistry, RegistryError


class RoutingError(ValueError):
    pass


class Router:
    """Route requests to registry capabilities; it never executes agents."""

    def __init__(self, registry: AgentRegistry) -> None:
        self.registry = registry

    def route(self, request: str, selected_agent_ids: list[str] | None = None) -> RoutingResult:
        if not request or not request.strip():
            raise RoutingError("request must not be empty")
        if selected_agent_ids is not None:
            return self._validate_selected_ids(selected_agent_ids, request)

        normalized = re.sub(r"[^a-z0-9_]+", "_", request.lower())
        normalized = normalized.replace("taxis", "taxi").replace("cabs", "cab")
        padded = f"_{normalized.strip('_')}_"
        selected: list[SelectedAgent] = []
        for agent in self.registry.list_enabled():
            matches = [cap for cap in agent.capabilities if f"_{cap.lower()}_" in padded]
            if matches:
                selected.append(SelectedAgent(agent.id, f"matched capability: {matches[0]}", request))
        if not selected:
            raise RoutingError("no enabled agent capability matched the request")
        return RoutingResult(tuple(selected))

    def _validate_selected_ids(self, agent_ids: list[str], request: str) -> RoutingResult:
        selected: list[SelectedAgent] = []
        for agent_id in agent_ids:
            try:
                self.registry.get(agent_id, enabled_only=True)
            except RegistryError as exc:
                raise RoutingError(str(exc)) from exc
            selected.append(SelectedAgent(agent_id, "selected by task analyzer", request))
        if not selected:
            raise RoutingError("routing result must select at least one agent")
        return RoutingResult(tuple(selected))
