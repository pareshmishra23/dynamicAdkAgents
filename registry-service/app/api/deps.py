from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from app.service.agent_service import AgentService
from app.service.mcp_server_service import McpServerService
from app.service.tool_service import ToolService


def get_mcp_server_service(request: Request) -> McpServerService:
    return request.app.state.services["mcp_servers"]


def get_agent_service(request: Request) -> AgentService:
    return request.app.state.services["agents"]


def get_tool_service(request: Request) -> ToolService:
    return request.app.state.services["tools"]


McpServerServiceDep = Annotated[McpServerService, Depends(get_mcp_server_service)]
AgentServiceDep = Annotated[AgentService, Depends(get_agent_service)]
ToolServiceDep = Annotated[ToolService, Depends(get_tool_service)]