from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.config.settings import DEFAULT_JAR
from app.main import create_app
from app.repository.database import H2Database


def _mem_url() -> str:
    return f"jdbc:h2:mem:{uuid.uuid4().hex};DB_CLOSE_DELAY=-1"


@pytest.fixture()
def db() -> H2Database:
    database = H2Database(url=_mem_url(), jar_path=DEFAULT_JAR)
    database.ensure_schema()
    yield database
    database.close()


@pytest.fixture()
def client(db: H2Database) -> TestClient:
    app = create_app(db=db)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def state(client: TestClient) -> dict:
    return {"client": client, "last": None}