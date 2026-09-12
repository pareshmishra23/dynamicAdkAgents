from __future__ import annotations

from app.model.mcp_server import McpServer, McpServerCreate
from app.repository.database import H2Database
from app.repository.mcp_server_repository import McpServerRepository

_TS = "2026-01-01T00:00:00.000Z"


def _server(server_id: str, name: str, enabled: bool = True) -> McpServer:
    return McpServer(
        **McpServerCreate(
            id=server_id,
            name=name,
            description=f"{name} tools",
            endpoint=f"stdio://{server_id}",
            transport="stdio",
            enabled=enabled,
            version="1.0.0",
        ).model_dump(),
        created_at=_TS,
        updated_at=_TS,
    )


class TestMcpServerRepository:
    def test_create_and_get(self, db: H2Database) -> None:
        repo = McpServerRepository(db)
        server = _server("taxi-tools", "Taxi Tools")
        repo.create(server)
        assert repo.get("taxi-tools") == server

    def test_get_missing_returns_none(self, db: H2Database) -> None:
        assert McpServerRepository(db).get("missing") is None

    def test_list_orders_and_filters_enabled(self, db: H2Database) -> None:
        repo = McpServerRepository(db)
        repo.create(_server("taxi-tools", "Taxi Tools", enabled=True))
        repo.create(_server("car-tools", "Car Tools", enabled=False))
        ids = [server.id for server in repo.list()]
        assert ids == ["car-tools", "taxi-tools"]
        active_ids = [server.id for server in repo.list(enabled=True)]
        assert active_ids == ["taxi-tools"]
        disabled_ids = [server.id for server in repo.list(enabled=False)]
        assert disabled_ids == ["car-tools"]

    def test_update_reflects_changes(self, db: H2Database) -> None:
        repo = McpServerRepository(db)
        repo.create(_server("taxi-tools", "Taxi Tools"))
        updated = _server("taxi-tools", "Taxi Search Pro")
        assert repo.update(updated) is True
        assert repo.get("taxi-tools").name == "Taxi Search Pro"

    def test_set_enabled(self, db: H2Database) -> None:
        repo = McpServerRepository(db)
        repo.create(_server("taxi-tools", "Taxi Tools"))
        assert repo.set_enabled("taxi-tools", False, _TS) is True
        assert repo.get("taxi-tools").enabled is False
        assert repo.set_enabled("taxi-tools", True, _TS) is True

    def test_delete(self, db: H2Database) -> None:
        repo = McpServerRepository(db)
        repo.create(_server("taxi-tools", "Taxi Tools"))
        assert repo.delete("taxi-tools") is True
        assert repo.get("taxi-tools") is None
        assert repo.delete("taxi-tools") is False

    def test_exists(self, db: H2Database) -> None:
        repo = McpServerRepository(db)
        assert repo.exists("taxi-tools") is False
        repo.create(_server("taxi-tools", "Taxi Tools"))
        assert repo.exists("taxi-tools") is True