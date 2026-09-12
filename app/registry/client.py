from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

from app.models import AgentDefinition, AgentLimits


class RegistryUnavailable(RuntimeError):
    pass


class RegistryMappingError(ValueError):
    pass


@dataclass(frozen=True)
class McpServerConfig:
    id: str
    name: str
    description: str
    endpoint: str
    transport: str
    enabled: bool
    version: str


def _http_request(url: str, method: str = "GET", body: bytes | None = None, timeout: float = 5.0) -> bytes:
    request = urllib.request.Request(url, data=body, method=method)
    if body is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError) as exc:
        raise RegistryUnavailable(f"registry unreachable at {url}: {exc}") from exc


def _parse_payload(raw: bytes, url: str) -> Any:
    try:
        return json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise RegistryUnavailable(f"registry returned non-JSON from {url}: {exc}") from exc


def map_registry_agent(payload: dict[str, Any], default_version: str = "registry") -> AgentDefinition:
    agent_id = str(payload.get("id") or "")
    if not agent_id:
        raise RegistryMappingError("registry agent missing required field: id")
    if not str(payload.get("name") or ""):
        raise RegistryMappingError("registry agent missing required field: name")
    policy = payload.get("policy") or {}
    if not isinstance(policy, dict):
        raise RegistryMappingError(f"policy must be a mapping for agent: {agent_id}")
    capabilities = payload.get("capabilities") or payload.get("capability")
    if not capabilities:
        raise RegistryMappingError("registry agent missing capabilities/capability")
    if isinstance(capabilities, str):
        capabilities = (capabilities,)
    config = payload.get("config") or {}
    allowed_tools = config.get("allowed_tools", ())
    contract = payload.get("output_contract")
    limits = AgentLimits(
        timeout_seconds=int(policy.get("timeout_seconds", 60)),
        max_tool_calls=int(policy.get("max_tool_calls", 5)),
    )
    return AgentDefinition(
        id=agent_id,
        version=str(payload.get("version") or default_version),
        enabled=bool(payload.get("enabled", True)),
        name=str(payload.get("name")),
        description=str(payload.get("description") or ""),
        capabilities=tuple(str(item) for item in capabilities),
        instructions=str(payload.get("instructions") or payload.get("description") or ""),
        input_contract={},
        output_contract=dict(contract or {}),
        allowed_tools=tuple(str(item) for item in (allowed_tools or ())),
        limits=limits,
        model=str(payload.get("model") or ""),
        requires_human_approval=bool(payload.get("requires_human_approval", False)),
        policy=dict(policy),
    )


def map_mcp_server(payload: dict[str, Any]) -> McpServerConfig:
    mcp_id = str(payload.get("id") or "")
    if not mcp_id:
        raise RegistryMappingError("registry MCP server missing required field: id")
    if not str(payload.get("endpoint") or ""):
        raise RegistryMappingError("registry MCP server missing required field: endpoint")
    return McpServerConfig(
        id=mcp_id,
        name=str(payload.get("name") or mcp_id),
        description=str(payload.get("description") or ""),
        endpoint=str(payload.get("endpoint")),
        transport=str(payload.get("transport") or "stdio"),
        enabled=bool(payload.get("enabled", True)),
        version=str(payload.get("version") or "registry"),
    )


class RegistryClient:
    def __init__(
        self,
        base_url: str,
        timeout: float = 5.0,
        transport: Callable[[str, str, bytes | None], bytes] | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._transport = transport or (lambda url, method, body: _http_request(url, method, body, timeout))

    def request_json(self, path: str, method: str = "GET", *, body: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url}{path}"
        payload = None if body is None else json.dumps(body).encode("utf-8")
        return _parse_payload(self._transport(url, method, payload), url)

    def fetch_enabled_agents(self) -> tuple[AgentDefinition, ...]:
        payload = self.request_json("/api/v1/agents?enabled=true")
        records = payload if isinstance(payload, list) else payload.get("items", [])
        return tuple(map_registry_agent(item) for item in records if isinstance(item, dict) and item.get("enabled"))

    def fetch_agent(self, agent_id: str) -> AgentDefinition:
        payload = self.request_json(f"/api/v1/agents/{agent_id}")
        return map_registry_agent(payload)

    def enable_agent(self, agent_id: str) -> AgentDefinition:
        return map_registry_agent(self.request_json(f"/api/v1/agents/{agent_id}/enable", method="PATCH"))

    def disable_agent(self, agent_id: str) -> AgentDefinition:
        return map_registry_agent(self.request_json(f"/api/v1/agents/{agent_id}/disable", method="PATCH"))

    def update_agent(self, agent_id: str, payload: dict[str, Any]) -> AgentDefinition:
        return map_registry_agent(self.request_json(f"/api/v1/agents/{agent_id}", method="PUT", body=payload))

    def fetch_enabled_mcp_servers(self) -> tuple[McpServerConfig, ...]:
        payload = self.request_json("/api/v1/mcp-servers?enabled=true")
        records = payload if isinstance(payload, list) else payload.get("items", [])
        return tuple(
            map_mcp_server(item)
            for item in records
            if isinstance(item, dict) and item.get("enabled") and item.get("endpoint")
        )