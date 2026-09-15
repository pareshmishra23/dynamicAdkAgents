from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

import jaydebeapi

from app.config.h2jar import ensure_h2_jar
from app.config.settings import DEFAULT_JAR


class H2Database:
    _SCHEMA_STATEMENTS: list[str] = [
        """
        CREATE TABLE IF NOT EXISTS mcp_servers (
            id VARCHAR(128) NOT NULL PRIMARY KEY,
            name VARCHAR(256) NOT NULL,
            description VARCHAR(1024) NOT NULL DEFAULT '',
            endpoint VARCHAR(1024) NOT NULL,
            transport VARCHAR(64) NOT NULL DEFAULT 'stdio',
            enabled BOOLEAN NOT NULL DEFAULT TRUE,
            version VARCHAR(64) NOT NULL,
            created_at VARCHAR(64) NOT NULL,
            updated_at VARCHAR(64) NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS agents (
            id VARCHAR(128) NOT NULL PRIMARY KEY,
            name VARCHAR(256) NOT NULL,
            description VARCHAR(1024) NOT NULL DEFAULT '',
            capability VARCHAR(512) NOT NULL,
            model VARCHAR(256) NOT NULL,
            enabled BOOLEAN NOT NULL DEFAULT TRUE,
            config VARCHAR(16384) NOT NULL DEFAULT '{}',
            policy VARCHAR(4096) NOT NULL DEFAULT '{}',
            output_contract VARCHAR(4096),
            requires_human_approval BOOLEAN NOT NULL DEFAULT FALSE,
            created_at VARCHAR(64) NOT NULL,
            updated_at VARCHAR(64) NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS tools (
            tool_id VARCHAR(128) NOT NULL PRIMARY KEY,
            name VARCHAR(256) NOT NULL,
            description VARCHAR(1024) NOT NULL DEFAULT '',
            capability VARCHAR(256) NOT NULL,
            provider VARCHAR(256) NOT NULL DEFAULT '',
            enabled BOOLEAN NOT NULL DEFAULT TRUE,
            config VARCHAR(4096) NOT NULL DEFAULT '{}',
            created_at VARCHAR(64) NOT NULL,
            updated_at VARCHAR(64) NOT NULL
        )
        """,
    ]

    def __init__(
        self,
        url: str,
        jar_path: Path | None = None,
        user: str = "sa",
        password: str = "",
    ) -> None:
        self.url = url
        self.jar_path = Path(jar_path) if jar_path else DEFAULT_JAR
        self.user = user
        self.password = password
        self._conn: Any | None = None
        self._lock = threading.RLock()

    @property
    def is_connected(self) -> bool:
        return self._conn is not None

    def _connection(self) -> Any:
        with self._lock:
            if self._conn is None:
                jar = ensure_h2_jar(self.jar_path)
                self._conn = jaydebeapi.connect(
                    "org.h2.Driver",
                    self.url,
                    [self.user, self.password],
                    str(jar),
                )
            return self._conn

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> int:
        with self._lock:
            cursor = self._connection().cursor()
            try:
                cursor.execute(sql, params)
                rowcount = cursor.rowcount
            finally:
                cursor.close()
        return rowcount if rowcount is not None else 0

    def query(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        with self._lock:
            conn = self._connection()
            cursor = conn.cursor()
            try:
                cursor.execute(sql, params)
                columns = [column[0].lower() for column in cursor.description]
                rows = cursor.fetchall()
            finally:
                cursor.close()
        return [dict(zip(columns, row)) for row in rows]

    def query_one(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def ensure_schema(self) -> None:
        for statement in self._SCHEMA_STATEMENTS:
            self.execute(statement)

    def close(self) -> None:
        with self._lock:
            conn, self._conn = self._conn, None
            if conn is not None:
                conn.close()

    def __enter__(self) -> "H2Database":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()