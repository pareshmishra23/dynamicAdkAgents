from __future__ import annotations

import pytest

from app.model.mcp_server import McpServerCreate, McpServerUpdate
from app.repository.database import H2Database
from app.repository.mcp_server_repository import McpServerRepository
from app.service.errors import DuplicateError, NotFoundError
from app.service.mcp_server_service import McpServerService


def _service(db: H2Database) -> McpServerService:
    return McpServerService(McpServerRepository(db))


class TestMcpServerService:
    def test_create_returns_model_with_timestamps(self, db: H2Database) -> None:
        created = _service(db).create(
            McpServerCreate(id="taxi-tools", name="Taxi", endpoint="stdio://taxi")
        )
        assert created.id == "taxi-tools"
        assert created.enabled is True
        assert created.created_at == created.updated_at
        assert created.created_at.endswith("Z")

    def test_duplicate_is_rejected(self, db: H2Database) -> None:
        service = _service(db)
        payload = McpServerCreate(id="taxi-tools", name="Taxi", endpoint="stdio://taxi")
        service.create(payload)
        with pytest.raises(DuplicateError):
            service.create(payload)

    def test_get_unknown_raises_not_found(self, db: H2Database) -> None:
        with pytest.raises(NotFoundError):
            _service(db).get("unknown")

    def test_update_preserves_created_at_and_bumps_updated_at(self, db: H2Database) -> None:
        service = _service(db)
        created = service.create(
            McpServerCreate(id="taxi-tools", name="Taxi", endpoint="stdio://taxi")
        )
        updated = service.update(
            "taxi-tools", McpServerUpdate(name="Taxi Pro", version="2.0.0")
        )
        assert updated.name == "Taxi Pro"
        assert updated.version == "2.0.0"
        assert updated.created_at == created.created_at

    def test_set_enabled_toggles_state(self, db: H2Database) -> None:
        service = _service(db)
        service.create(McpServerCreate(id="taxi-tools", name="Taxi", endpoint="stdio://taxi"))
        disabled = service.set_enabled("taxi-tools", False)
        assert disabled.enabled is False
        enabled = service.set_enabled("taxi-tools", True)
        assert enabled.enabled is True

    def test_set_enabled_is_idempotent(self, db: H2Database) -> None:
        service = _service(db)
        service.create(McpServerCreate(id="taxi-tools", name="Taxi", endpoint="stdio://taxi"))
        service.set_enabled("taxi-tools", False)
        again = service.set_enabled("taxi-tools", False)
        assert again.enabled is False

    def test_delete_raises_not_found_for_missing(self, db: H2Database) -> None:
        with pytest.raises(NotFoundError):
            _service(db).delete("unknown")