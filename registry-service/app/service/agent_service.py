from __future__ import annotations

from app.model.agent import Agent, AgentCreate, AgentPolicy, AgentUpdate
from app.repository.agent_repository import AgentRepository
from app.service.errors import DuplicateError, NotFoundError
from app.service.timeutils import utcnow


class AgentService:
    def __init__(self, repository: AgentRepository) -> None:
        self._repository = repository

    def create(self, data: AgentCreate) -> Agent:
        if self._repository.exists(data.id):
            raise DuplicateError("agent", data.id)
        now = utcnow()
        payload = data.model_dump()
        payload["policy"] = payload["policy"] or AgentPolicy()
        agent = Agent(**payload, created_at=now, updated_at=now)
        return self._repository.create(agent)

    def get(self, agent_id: str) -> Agent:
        agent = self._repository.get(agent_id)
        if agent is None:
            raise NotFoundError("agent", agent_id)
        return agent

    def list(self, enabled: bool | None = None) -> list[Agent]:
        return self._repository.list(enabled=enabled)

    def update(self, agent_id: str, data: AgentUpdate) -> Agent:
        current = self.get(agent_id)
        changes = data.model_dump(exclude_unset=True)
        if not changes:
            return current
        policy_changes = changes.pop("policy", None)
        if policy_changes is not None:
            changes["policy"] = current.policy.model_copy(update=policy_changes)
        updated = current.model_copy(update={**changes, "updated_at": utcnow()})
        self._repository.update(updated)
        return updated

    def set_enabled(self, agent_id: str, enabled: bool) -> Agent:
        current = self.get(agent_id)
        if current.enabled == enabled:
            return current
        now = utcnow()
        updated = current.model_copy(update={"enabled": enabled, "updated_at": now})
        self._repository.set_enabled(agent_id, enabled, now)
        return updated

    def delete(self, agent_id: str) -> None:
        if not self._repository.delete(agent_id):
            raise NotFoundError("agent", agent_id)