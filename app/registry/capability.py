from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.registry.client import McpServerConfig, RegistryClient, ToolRegistration


class CapabilityError(ValueError):
    pass


class CapabilityNotFoundError(CapabilityError):
    pass


class ProviderUnavailableError(CapabilityError):
    pass


@dataclass(frozen=True)
class ResolvedProvider:
    capability: str
    tool_id: str
    tool_name: str
    tool_description: str
    provider_id: str
    endpoint: str
    transport: str
    config: dict[str, Any]


class CapabilityResolver:
    """Resolves abstract capabilities to concrete providers via Tool and MCP registries.

    Enables complete provider independence:
    Agents declare: 'I need: route_optimization'
    Resolver: Capability -> Tool Registry -> MCP Registry -> Concrete Provider.
    """

    def __init__(self, registry_client: RegistryClient) -> None:
        self.registry_client = registry_client

    def resolve_capability(self, capability: str) -> ResolvedProvider:
        normalized_cap = capability.strip().lower()

        # Step 1: Query Tool Registry for enabled tools matching capability
        tools = self.registry_client.fetch_tools(enabled=True, capability=normalized_cap)
        if not tools:
            # Fallback: scan all enabled tools if exact query returned none
            all_tools = self.registry_client.fetch_tools(enabled=True)
            tools = tuple(t for t in all_tools if t.capability.strip().lower() == normalized_cap)

        if not tools:
            raise CapabilityNotFoundError(f"no enabled tool registered for capability: {capability}")

        selected_tool = tools[0]

        # Step 2: Query MCP Registry for provider endpoint
        provider_id = selected_tool.provider
        if not provider_id:
            # Built-in or local provider without external MCP server
            return ResolvedProvider(
                capability=normalized_cap,
                tool_id=selected_tool.tool_id,
                tool_name=selected_tool.name,
                tool_description=selected_tool.description,
                provider_id="builtin",
                endpoint="builtin://local",
                transport="local",
                config=selected_tool.config,
            )

        try:
            mcp_server = self.registry_client.fetch_mcp_server(provider_id)
        except Exception as exc:
            raise ProviderUnavailableError(
                f"provider {provider_id} for capability {capability} could not be retrieved: {exc}"
            ) from exc

        if not mcp_server.enabled:
            raise ProviderUnavailableError(f"provider {provider_id} for capability {capability} is disabled")

        return ResolvedProvider(
            capability=normalized_cap,
            tool_id=selected_tool.tool_id,
            tool_name=selected_tool.name,
            tool_description=selected_tool.description,
            provider_id=mcp_server.id,
            endpoint=mcp_server.endpoint,
            transport=mcp_server.transport,
            config=selected_tool.config,
        )

    def resolve_many(self, capabilities: tuple[str, ...]) -> tuple[ResolvedProvider, ...]:
        return tuple(self.resolve_capability(cap) for cap in capabilities)
