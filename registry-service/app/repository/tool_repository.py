from __future__ import annotations

import json
from typing import Any

from app.model.tool import Tool
from app.repository.database import H2Database

_SELECT = (
    "SELECT tool_id, name, description, capability, provider, enabled, config,"
    " created_at, updated_at FROM tools"
)


def _from_row(row: dict[str, Any]) -> Tool:
    raw_config = row.get("config") or "{}"
    if isinstance(raw_config, str):
        try:
            config = json.loads(raw_config)
        except Exception:
            config = {}
    else:
        config = raw_config if isinstance(raw_config, dict) else {}

    return Tool(
        tool_id=row["tool_id"],
        name=row["name"],
        description=row["description"],
        capability=row["capability"],
        provider=row["provider"],
        enabled=bool(row["enabled"]),
        config=config,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class ToolRepository:
    def __init__(self, db: H2Database) -> None:
        self._db = db

    def create(self, tool: Tool) -> Tool:
        self._db.execute(
            "INSERT INTO tools"
            " (tool_id, name, description, capability, provider, enabled, config,"
            " created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                tool.tool_id,
                tool.name,
                tool.description,
                tool.capability,
                tool.provider,
                tool.enabled,
                json.dumps(tool.config),
                tool.created_at,
                tool.updated_at,
            ),
        )
        return tool

    def get(self, tool_id: str) -> Tool | None:
        row = self._db.query_one(f"{_SELECT} WHERE tool_id = ?", (tool_id,))
        return _from_row(row) if row else None

    def list(self, enabled: bool | None = None, capability: str | None = None) -> list[Tool]:
        clauses: list[str] = []
        params: list[Any] = []
        if enabled is not None:
            clauses.append("enabled = TRUE" if enabled else "enabled = FALSE")
        if capability is not None:
            clauses.append("LOWER(capability) = ?")
            params.append(capability.lower().strip())

        sql = _SELECT
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY name ASC"
        return [_from_row(row) for row in self._db.query(sql, tuple(params))]

    def update(self, tool: Tool) -> bool:
        affected = self._db.execute(
            "UPDATE tools SET name = ?, description = ?, capability = ?,"
            " provider = ?, config = ?, updated_at = ? WHERE tool_id = ?",
            (
                tool.name,
                tool.description,
                tool.capability,
                tool.provider,
                json.dumps(tool.config),
                tool.updated_at,
                tool.tool_id,
            ),
        )
        return affected > 0

    def set_enabled(self, tool_id: str, enabled: bool, updated_at: str) -> bool:
        affected = self._db.execute(
            "UPDATE tools SET enabled = ?, updated_at = ? WHERE tool_id = ?",
            (enabled, updated_at, tool_id),
        )
        return affected > 0

    def delete(self, tool_id: str) -> bool:
        affected = self._db.execute(
            "DELETE FROM tools WHERE tool_id = ?", (tool_id,)
        )
        return affected > 0

    def exists(self, tool_id: str) -> bool:
        row = self._db.query_one("SELECT 1 AS present FROM tools WHERE tool_id = ?", (tool_id,))
        return row is not None
