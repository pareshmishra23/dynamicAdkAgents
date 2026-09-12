from __future__ import annotations

from app.model.mcp_server import McpServer, McpServerCreate, McpServerUpdate
from app.repository.mcp_server_repository import McpServerRepository
from app.service.errors import DuplicateError, NotFoundError
from app.service.timeutils import utcnow


class McpServerService:
    def __init__(self, repository: McpServerRepository) -> None:
        self._repository = repository

    def create(self, data: McpServerCreate) -> McpServer:
        if self._repository.exists(data.id):
            raise DuplicateError("mcp-server", data.id)
        now = utcnow()
        server = McpServer(**data.model_dump(), created_at=now, updated_at=now)
        return self._repository.create(server)

    def get(self, server_id: str) -> McpServer:
        server = self._repository.get(server_id)
        if server is None:
            raise NotFoundError("mcp-server", server_id)
        return server

    def list(self, enabled: bool | None = None) -> list[McpServer]:
        return self._repository.list(enabled=enabled)

    def update(self, server_id: str, data: McpServerUpdate) -> McpServer:
        current = self.get(server_id)
        changes = data.model_dump(exclude_unset=True)
        if not changes:
            return current
        updated = current.model_copy(update={**changes, "updated_at": utcnow()})
        self._repository.update(updated)
        return updated

    def set_enabled(self, server_id: str, enabled: bool) -> McpServer:
        current = self.get(server_id)
        if current.enabled == enabled:
            return current
        updated = current.model_copy(update={"enabled": enabled, "updated_at": utcnow()})
        self._repository.update(updated)
        return updated

    def delete(self, server_id: str) -> None:
        if not self._repository.delete(server_id):
            raise NotFoundError("mcp-server", server_id)