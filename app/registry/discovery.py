from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable

from app.registry.client import McpServerConfig, RegistryClient, ToolRegistration


class McpDiscoveryError(RuntimeError):
    pass


@dataclass(frozen=True)
class DiscoveredMcpTool:
    tool_id: str
    name: str
    description: str
    capability: str
    provider: str
    enabled: bool = True
    config: dict[str, Any] | None = None


class McpToolDiscovery:
    """Discovers tools exposed by MCP servers and registers them dynamically in the Tool Registry."""

    def __init__(
        self,
        registry_client: RegistryClient,
        mcp_caller: Callable[[McpServerConfig, str], dict[str, Any]] | None = None,
    ) -> None:
        self.registry_client = registry_client
        self._mcp_caller = mcp_caller or self._default_mcp_caller

    def _default_mcp_caller(self, server: McpServerConfig, action: str) -> dict[str, Any]:
        """Fetch tool catalog from the MCP server endpoint."""
        import urllib.request

        if server.transport == "http":
            endpoint = server.endpoint.rstrip("/")
            url = f"{endpoint}/tools"
            req = urllib.request.Request(url, method="GET")
            req.add_header("Accept", "application/json")
            try:
                with urllib.request.urlopen(req, timeout=5.0) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except Exception as exc:
                raise McpDiscoveryError(f"failed to query MCP server {server.id} at {url}: {exc}") from exc
        # Default mock manifest for stdio/test transports
        return {"tools": []}

    def discover_and_register(self, server: McpServerConfig) -> tuple[ToolRegistration, ...]:
        """Discover tools from an MCP server and register them in the Tool Registry."""
        if not server.enabled:
            return ()

        catalog = self._mcp_caller(server, "list_tools")
        raw_tools = catalog.get("tools") or []
        registered: list[ToolRegistration] = []

        for raw in raw_tools:
            tool_id = raw.get("tool_id") or raw.get("id") or raw.get("name")
            capability = raw.get("capability") or "general"
            tool_payload = {
                "tool_id": str(tool_id),
                "name": str(raw.get("name") or tool_id),
                "description": str(raw.get("description") or ""),
                "capability": str(capability),
                "provider": server.id,
                "enabled": bool(raw.get("enabled", True)),
                "config": raw.get("config") or {},
            }
            try:
                tool_reg = self.registry_client.register_tool(tool_payload)
            except Exception:
                # If already exists, update it to reflect current MCP provider state
                tool_reg = self.registry_client.update_tool(str(tool_id), tool_payload)
            registered.append(tool_reg)

        return tuple(registered)

    def discover_all_enabled(self) -> tuple[ToolRegistration, ...]:
        """Discover tools across all enabled MCP servers in the registry."""
        servers = self.registry_client.fetch_enabled_mcp_servers()
        all_registered: list[ToolRegistration] = []
        for server in servers:
            all_registered.extend(self.discover_and_register(server))
        return tuple(all_registered)
