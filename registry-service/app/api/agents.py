from __future__ import annotations

from fastapi import APIRouter, Query, Response

from app.api.deps import AgentServiceDep
from app.model.agent import Agent, AgentCreate, AgentUpdate

router = APIRouter(prefix="/agents")


@router.post("", response_model=Agent, status_code=201)
def create_agent(
    payload: AgentCreate,
    service: AgentServiceDep,
) -> Agent:
    return service.create(payload)


@router.get("", response_model=list[Agent])
def list_agents(
    service: AgentServiceDep,
    enabled: bool | None = Query(default=None),
) -> list[Agent]:
    if enabled is None:
        return service.list()
    return service.list(enabled=enabled)


@router.get("/{agent_id}", response_model=Agent)
def get_agent(
    agent_id: str,
    service: AgentServiceDep,
) -> Agent:
    return service.get(agent_id)


@router.put("/{agent_id}", response_model=Agent)
def update_agent(
    agent_id: str,
    payload: AgentUpdate,
    service: AgentServiceDep,
) -> Agent:
    return service.update(agent_id, payload)


@router.patch("/{agent_id}/enable", response_model=Agent)
def enable_agent(
    agent_id: str,
    service: AgentServiceDep,
) -> Agent:
    return service.set_enabled(agent_id, True)


@router.patch("/{agent_id}/disable", response_model=Agent)
def disable_agent(
    agent_id: str,
    service: AgentServiceDep,
) -> Agent:
    return service.set_enabled(agent_id, False)


@router.delete("/{agent_id}", status_code=204)
def delete_agent(
    agent_id: str,
    service: AgentServiceDep,
) -> Response:
    service.delete(agent_id)
    return Response(status_code=204)