from __future__ import annotations

import json
from typing import Any

from app.model.agent import Agent, AgentPolicy, OutputContract
from app.repository.database import H2Database

_SELECT = (
    "SELECT id, name, description, capability, model, enabled, config, policy,"
    " output_contract, requires_human_approval, created_at, updated_at FROM agents"
)


def _from_row(row: dict[str, Any]) -> Agent:
    raw_config = row["config"] or "{}"
    raw_policy = row["policy"] or "{}"
    raw_contract = row["output_contract"]
    return Agent(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        capability=row["capability"],
        model=row["model"],
        enabled=bool(row["enabled"]),
        config=json.loads(raw_config),
        policy=AgentPolicy.model_validate_json(raw_policy),
        output_contract=OutputContract.model_validate_json(raw_contract) if raw_contract else None,
        requires_human_approval=bool(row["requires_human_approval"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class AgentRepository:
    def __init__(self, db: H2Database) -> None:
        self._db = db

    def create(self, agent: Agent) -> Agent:
        self._db.execute(
            "INSERT INTO agents"
            " (id, name, description, capability, model, enabled, config, policy,"
            " output_contract, requires_human_approval, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                agent.id,
                agent.name,
                agent.description,
                agent.capability,
                agent.model,
                agent.enabled,
                json.dumps(agent.config, default=str),
                json.dumps(agent.policy.model_dump(), default=str),
                json.dumps(agent.output_contract.model_dump()) if agent.output_contract else None,
                agent.requires_human_approval,
                agent.created_at,
                agent.updated_at,
            ),
        )
        return agent

    def get(self, agent_id: str) -> Agent | None:
        row = self._db.query_one(f"{_SELECT} WHERE id = ?", (agent_id,))
        return _from_row(row) if row else None

    def list(self, enabled: bool | None = None) -> list[Agent]:
        sql = _SELECT
        if enabled is not None:
            sql += " WHERE enabled = TRUE" if enabled else " WHERE enabled = FALSE"
        sql += " ORDER BY name ASC"
        return [_from_row(row) for row in self._db.query(sql)]

    def update(self, agent: Agent) -> bool:
        affected = self._db.execute(
            "UPDATE agents SET name = ?, description = ?, capability = ?,"
            " model = ?, enabled = ?, config = ?, policy = ?, output_contract = ?,"
            " requires_human_approval = ?, updated_at = ? WHERE id = ?",
            (
                agent.name,
                agent.description,
                agent.capability,
                agent.model,
                agent.enabled,
                json.dumps(agent.config, default=str),
                json.dumps(agent.policy.model_dump(), default=str),
                json.dumps(agent.output_contract.model_dump()) if agent.output_contract else None,
                agent.requires_human_approval,
                agent.updated_at,
                agent.id,
            ),
        )
        return affected > 0

    def set_enabled(self, agent_id: str, enabled: bool, updated_at: str) -> bool:
        affected = self._db.execute(
            "UPDATE agents SET enabled = ?, updated_at = ? WHERE id = ?",
            (enabled, updated_at, agent_id),
        )
        return affected > 0

    def delete(self, agent_id: str) -> bool:
        affected = self._db.execute("DELETE FROM agents WHERE id = ?", (agent_id,))
        return affected > 0

    def exists(self, agent_id: str) -> bool:
        row = self._db.query_one("SELECT 1 AS present FROM agents WHERE id = ?", (agent_id,))
        return row is not None