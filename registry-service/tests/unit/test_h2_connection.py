from __future__ import annotations

from app.repository.database import H2Database


class TestH2Connection:
    def test_engine_is_real_h2(self, db: H2Database) -> None:
        row = db.query_one("SELECT H2VERSION() AS version")
        assert row is not None
        assert row["version"].startswith("2.")

    def test_ddl_and_roundtrip(self, db: H2Database) -> None:
        db.execute("CREATE TABLE ping_test (id VARCHAR(32), message VARCHAR(128))")
        db.execute("INSERT INTO ping_test (id, message) VALUES (?, ?)", ("a", "ready"))
        row = db.query_one("SELECT message FROM ping_test WHERE id = ?", ("a",))
        assert row == {"message": "ready"}

    def test_schema_contains_registry_tables(self, db: H2Database) -> None:
        tables = {
            row["table_name"].upper()
            for row in db.query("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'PUBLIC'")
        }
        assert {"MCP_SERVERS", "AGENTS"}.issubset(tables)