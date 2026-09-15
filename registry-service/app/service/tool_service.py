from __future__ import annotations

from app.model.tool import Tool, ToolCreate, ToolUpdate
from app.repository.tool_repository import ToolRepository
from app.service.errors import DuplicateError, NotFoundError
from app.service.timeutils import utcnow


class ToolService:
    def __init__(self, repository: ToolRepository) -> None:
        self._repository = repository

    def create(self, data: ToolCreate) -> Tool:
        if self._repository.exists(data.tool_id):
            raise DuplicateError("tool", data.tool_id)
        now = utcnow()
        tool = Tool(**data.model_dump(), created_at=now, updated_at=now)
        return self._repository.create(tool)

    def get(self, tool_id: str) -> Tool:
        tool = self._repository.get(tool_id)
        if tool is None:
            raise NotFoundError("tool", tool_id)
        return tool

    def list(self, enabled: bool | None = None, capability: str | None = None) -> list[Tool]:
        return self._repository.list(enabled=enabled, capability=capability)

    def update(self, tool_id: str, data: ToolUpdate) -> Tool:
        current = self.get(tool_id)
        changes = data.model_dump(exclude_unset=True)
        if not changes:
            return current
        updated = current.model_copy(update={**changes, "updated_at": utcnow()})
        self._repository.update(updated)
        return updated

    def set_enabled(self, tool_id: str, enabled: bool) -> Tool:
        current = self.get(tool_id)
        if current.enabled == enabled:
            return current
        updated = current.model_copy(update={"enabled": enabled, "updated_at": utcnow()})
        self._repository.update(updated)
        return updated

    def delete(self, tool_id: str) -> None:
        if not self._repository.delete(tool_id):
            raise NotFoundError("tool", tool_id)
