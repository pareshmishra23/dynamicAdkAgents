from __future__ import annotations

from app.model.agent import Agent, AgentCreate, AgentPolicy
from app.repository.agent_repository import AgentRepository
from app.repository.database import H2Database

_TS = "2026-01-01T00:00:00.000Z"


def _agent(
    agent_id: str,
    name: str,
    enabled: bool = True,
    capability: str = "general",
    policy: AgentPolicy | None = None,
) -> Agent:
    return Agent(
        **{
            **AgentCreate(
                id=agent_id,
                name=name,
                description=f"{name} agent",
                capability=capability,
                model="local-model",
                enabled=enabled,
                config={"region": "nyc"},
            ).model_dump(),
            "policy": policy or AgentPolicy(),
        },
        created_at=_TS,
        updated_at=_TS,
    )


class TestAgentRepository:
    def test_create_and_get(self, db: H2Database) -> None:
        repo = AgentRepository(db)
        agent = _agent("taxi_agent", "Taxi Agent")
        repo.create(agent)
        assert repo.get("taxi_agent") == agent

    def test_config_roundtrip(self, db: H2Database) -> None:
        repo = AgentRepository(db)
        repo.create(_agent("taxi_agent", "Taxi Agent"))
        assert repo.get("taxi_agent").config == {"region": "nyc"}

    def test_policy_roundtrip(self, db: H2Database) -> None:
        repo = AgentRepository(db)
        repo.create(
            _agent(
                "taxi_agent",
                "Taxi Agent",
                policy=AgentPolicy(temperature=0.2, seed=42, max_tool_calls=8),
            )
        )
        assert repo.get("taxi_agent").policy == AgentPolicy(
            temperature=0.2, seed=42, max_tool_calls=8
        )
        assert repo.get("taxi_agent").policy.timeout_seconds == 60

    def test_get_missing_returns_none(self, db: H2Database) -> None:
        assert AgentRepository(db).get("missing") is None

    def test_list_orders_and_filters_enabled(self, db: H2Database) -> None:
        repo = AgentRepository(db)
        repo.create(_agent("taxi_agent", "Taxi Agent", enabled=True))
        repo.create(_agent("car_agent", "Car Agent", enabled=False))
        ids = [agent.id for agent in repo.list()]
        assert ids == ["car_agent", "taxi_agent"]
        active_ids = [agent.id for agent in repo.list(enabled=True)]
        assert active_ids == ["taxi_agent"]
        disabled_ids = [agent.id for agent in repo.list(enabled=False)]
        assert disabled_ids == ["car_agent"]

    def test_update_reflects_changes(self, db: H2Database) -> None:
        repo = AgentRepository(db)
        repo.create(_agent("taxi_agent", "Taxi Agent"))
        updated = _agent("taxi_agent", "Taxi Specialist", capability="taxi-search")
        assert repo.update(updated) is True
        got = repo.get("taxi_agent")
        assert got.name == "Taxi Specialist"
        assert got.capability == "taxi-search"

    def test_set_enabled(self, db: H2Database) -> None:
        repo = AgentRepository(db)
        repo.create(_agent("taxi_agent", "Taxi Agent"))
        assert repo.set_enabled("taxi_agent", False, _TS) is True
        assert repo.get("taxi_agent").enabled is False

    def test_delete(self, db: H2Database) -> None:
        repo = AgentRepository(db)
        repo.create(_agent("taxi_agent", "Taxi Agent"))
        assert repo.delete("taxi_agent") is True
        assert repo.get("taxi_agent") is None
        assert repo.delete("taxi_agent") is False