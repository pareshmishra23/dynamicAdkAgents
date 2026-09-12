from __future__ import annotations

import pytest

from app.model.agent import AgentCreate, AgentPolicy, AgentUpdate, OutputContract
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

    def test_create_applies_default_deterministic_policy(self, db: H2Database) -> None:
        created = _service(db).create(
            AgentCreate(id="taxi_agent", name="Taxi", capability="taxi-search")
        )
        assert created.policy == AgentPolicy()
        assert created.policy.temperature == 0.0
        assert created.policy.timeout_seconds == 60

    def test_create_accepts_explicit_policy(self, db: H2Database) -> None:
        created = _service(db).create(
            AgentCreate(
                id="taxi_agent",
                name="Taxi",
                capability="taxi-search",
                policy=AgentPolicy(temperature=0.5, seed=7),
            )
        )
        assert created.policy.temperature == 0.5
        assert created.policy.seed == 7

    def test_update_merges_policy_partially(self, db: H2Database) -> None:
        service = _service(db)
        service.create(
            AgentCreate(
                id="taxi_agent",
                name="Taxi",
                capability="taxi-search",
                policy=AgentPolicy(temperature=0.5, seed=7, max_tool_calls=9),
            )
        )
        updated = service.update(
            "taxi_agent", AgentUpdate(policy=AgentPolicy(temperature=0.0))
        )
        assert updated.policy.temperature == 0.0
        assert updated.policy.seed == 7
        assert updated.policy.max_tool_calls == 9

    def test_create_and_update_output_contract_and_hitl_flag(self, db: H2Database) -> None:
        service = _service(db)
        contract = OutputContract(required=["summary", "confidence"])
        created = service.create(
            AgentCreate(
                id="car_agent",
                name="Car",
                capability="car-rental",
                output_contract=contract,
                requires_human_approval=True,
            )
        )
        assert created.requires_human_approval is True
        assert created.output_contract == contract

        updated = service.update(
            "car_agent", AgentUpdate(requires_human_approval=False)
        )
        assert updated.requires_human_approval is False
        assert updated.output_contract == contract

    def test_delete_raises_not_found_for_missing(self, db: H2Database) -> None:
        with pytest.raises(NotFoundError):
            _service(db).delete("unknown")