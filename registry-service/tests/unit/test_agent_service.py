from __future__ import annotations

import pytest

from app.model.agent import AgentCreate, AgentUpdate
from app.repository.agent_repository import AgentRepository
from app.repository.database import H2Database
from app.service.agent_service import AgentService
from app.service.errors import DuplicateError, NotFoundError


def _service(db: H2Database) -> AgentService:
    return AgentService(AgentRepository(db))


class TestAgentService:
    def test_create_returns_model_with_timestamps(self, db: H2Database) -> None:
        created = _service(db).create(
            AgentCreate(id="taxi_agent", name="Taxi", capability="taxi-search")
        )
        assert created.id == "taxi_agent"
        assert created.enabled is True
        assert created.created_at == created.updated_at
        assert created.created_at.endswith("Z")

    def test_duplicate_is_rejected(self, db: H2Database) -> None:
        service = _service(db)
        payload = AgentCreate(id="taxi_agent", name="Taxi", capability="taxi-search")
        service.create(payload)
        with pytest.raises(DuplicateError):
            service.create(payload)

    def test_get_unknown_raises_not_found(self, db: H2Database) -> None:
        with pytest.raises(NotFoundError):
            _service(db).get("unknown")

    def test_update_preserves_created_at(self, db: H2Database) -> None:
        service = _service(db)
        created = service.create(
            AgentCreate(id="taxi_agent", name="Taxi", capability="taxi-search")
        )
        updated = service.update(
            "taxi_agent",
            AgentUpdate(capability="taxi-book", model="gemini-flash"),
        )
        assert updated.capability == "taxi-book"
        assert updated.model == "gemini-flash"
        assert updated.created_at == created.created_at

    def test_set_enabled_toggles_state(self, db: H2Database) -> None:
        service = _service(db)
        service.create(AgentCreate(id="taxi_agent", name="Taxi", capability="taxi-search"))
        disabled = service.set_enabled("taxi_agent", False)
        assert disabled.enabled is False
        enabled = service.set_enabled("taxi_agent", True)
        assert enabled.enabled is True

    def test_delete_raises_not_found_for_missing(self, db: H2Database) -> None:
        with pytest.raises(NotFoundError):
            _service(db).delete("unknown")