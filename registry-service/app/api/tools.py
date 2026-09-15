from __future__ import annotations

from fastapi import APIRouter, Query, Response

from app.api.deps import ToolServiceDep
from app.model.tool import Tool, ToolCreate, ToolUpdate

router = APIRouter(prefix="/tools")


@router.post("", response_model=Tool, status_code=201)
def create_tool(
    payload: ToolCreate,
    service: ToolServiceDep,
) -> Tool:
    return service.create(payload)


@router.get("", response_model=list[Tool])
def list_tools(
    service: ToolServiceDep,
    enabled: bool | None = Query(default=None),
    capability: str | None = Query(default=None),
) -> list[Tool]:
    return service.list(enabled=enabled, capability=capability)


@router.get("/{tool_id}", response_model=Tool)
def get_tool(
    tool_id: str,
    service: ToolServiceDep,
) -> Tool:
    return service.get(tool_id)


@router.put("/{tool_id}", response_model=Tool)
def update_tool(
    tool_id: str,
    payload: ToolUpdate,
    service: ToolServiceDep,
) -> Tool:
    return service.update(tool_id, payload)


@router.patch("/{tool_id}/enable", response_model=Tool)
def enable_tool(
    tool_id: str,
    service: ToolServiceDep,
) -> Tool:
    return service.set_enabled(tool_id, True)


@router.patch("/{tool_id}/disable", response_model=Tool)
def disable_tool(
    tool_id: str,
    service: ToolServiceDep,
) -> Tool:
    return service.set_enabled(tool_id, False)


@router.delete("/{tool_id}", status_code=204)
def delete_tool(
    tool_id: str,
    service: ToolServiceDep,
) -> Response:
    service.delete(tool_id)
    return Response(status_code=204)
