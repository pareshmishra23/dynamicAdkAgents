from __future__ import annotations

from typing import Any

from app.model.mcp_server import McpServer
from app.repository.database import H2Database

_SELECT = (
    "SELECT id, name, description, endpoint, transport, enabled, version,"
    " created_at, updated_at FROM mcp_servers"
)


def _from_row(row: dict[str, Any]) -> McpServer:
    return McpServer(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        endpoint=row["endpoint"],
        transport=row["transport"],
        enabled=bool(row["enabled"]),
        version=row["version"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class McpServerRepository:
    def __init__(self, db: H2Database) -> None:
        self._db = db

    def create(self, server: McpServer) -> McpServer:
        self._db.execute(
            "INSERT INTO mcp_servers"
            " (id, name, description, endpoint, transport, enabled, version,"
            " created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                server.id,
                server.name,
                server.description,
                server.endpoint,
                server.transport,
                server.enabled,
                server.version,
                server.created_at,
                server.updated_at,
            ),
        )
        return server

    def get(self, server_id: str) -> McpServer | None:
        row = self._db.query_one(f"{_SELECT} WHERE id = ?", (server_id,))
        return _from_row(row) if row else None

    def list(self, enabled: bool | None = None) -> list[McpServer]:
        sql = _SELECT
        if enabled is not None:
            sql += " WHERE enabled = TRUE" if enabled else " WHERE enabled = FALSE"
        sql += " ORDER BY name ASC"
        return [_from_row(row) for row in self._db.query(sql)]

    def update(self, server: McpServer) -> bool:
        affected = self._db.execute(
            "UPDATE mcp_servers SET name = ?, description = ?, endpoint = ?,"
            " transport = ?, version = ?, updated_at = ? WHERE id = ?",
            (
                server.name,
                server.description,
                server.endpoint,
                server.transport,
                server.version,
                server.updated_at,
                server.id,
            ),
        )
        return affected > 0

    def set_enabled(self, server_id: str, enabled: bool, updated_at: str) -> bool:
        affected = self._db.execute(
            "UPDATE mcp_servers SET enabled = ?, updated_at = ? WHERE id = ?",
            (enabled, updated_at, server_id),
        )
        return affected > 0

    def delete(self, server_id: str) -> bool:
        affected = self._db.execute(
            "DELETE FROM mcp_servers WHERE id = ?", (server_id,)
        )
        return affected > 0

    def exists(self, server_id: str) -> bool:
        row = self._db.query_one("SELECT 1 AS present FROM mcp_servers WHERE id = ?", (server_id,))
        return row is not None