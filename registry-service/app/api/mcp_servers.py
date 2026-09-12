from __future__ import annotations

from fastapi import APIRouter, Query, Response

from app.api.deps import McpServerServiceDep
from app.model.mcp_server import McpServer, McpServerCreate, McpServerUpdate

router = APIRouter(prefix="/mcp-servers")


@router.post("", response_model=McpServer, status_code=201)
def create_mcp_server(
    payload: McpServerCreate,
    service: McpServerServiceDep,
) -> McpServer:
    return service.create(payload)


@router.get("", response_model=list[McpServer])
def list_mcp_servers(
    service: McpServerServiceDep,
    enabled: bool | None = Query(default=None),
) -> list[McpServer]:
    if enabled is None:
        return service.list()
    return service.list(enabled=enabled)


@router.get("/{server_id}", response_model=McpServer)
def get_mcp_server(
    server_id: str,
    service: McpServerServiceDep,
) -> McpServer:
    return service.get(server_id)


@router.put("/{server_id}", response_model=McpServer)
def update_mcp_server(
    server_id: str,
    payload: McpServerUpdate,
    service: McpServerServiceDep,
) -> McpServer:
    return service.update(server_id, payload)


@router.patch("/{server_id}/enable", response_model=McpServer)
def enable_mcp_server(
    server_id: str,
    service: McpServerServiceDep,
) -> McpServer:
    return service.set_enabled(server_id, True)


@router.patch("/{server_id}/disable", response_model=McpServer)
def disable_mcp_server(
    server_id: str,
    service: McpServerServiceDep,
) -> McpServer:
    return service.set_enabled(server_id, False)


@router.delete("/{server_id}", status_code=204)
def delete_mcp_server(
    server_id: str,
    service: McpServerServiceDep,
) -> Response:
    service.delete(server_id)
    return Response(status_code=204)