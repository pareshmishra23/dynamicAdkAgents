from __future__ import annotations

from fastapi.testclient import TestClient

MCP_PAYLOAD = {
    "id": "taxi-tools",
    "name": "Taxi Tools",
    "description": "taxi search",
    "endpoint": "stdio://taxi-tools",
    "transport": "stdio",
    "enabled": True,
    "version": "1.0.0",
}

AGENT_PAYLOAD = {
    "id": "taxi_agent",
    "name": "Taxi Agent",
    "description": "taxi specialist",
    "capability": "taxi-search",
    "model": "local-model",
    "enabled": True,
    "config": {"region": "nyc"},
}


class TestMcpServerApi:
    def test_full_crud_flow(self, client: TestClient) -> None:
        created = client.post("/api/v1/mcp-servers", json=MCP_PAYLOAD)
        assert created.status_code == 201
        body = created.json()
        assert body["id"] == "taxi-tools"
        assert body["enabled"] is True
        assert body["created_at"].endswith("Z")

        items = client.get("/api/v1/mcp-servers").json()
        assert [item["id"] for item in items] == ["taxi-tools"]

        fetched = client.get("/api/v1/mcp-servers/taxi-tools")
        assert fetched.status_code == 200
        assert fetched.json()["endpoint"] == "stdio://taxi-tools"

        updated = client.put(
            "/api/v1/mcp-servers/taxi-tools", json={"name": "Taxi Search Pro", "version": "2.0.0"}
        )
        assert updated.status_code == 200
        assert updated.json()["name"] == "Taxi Search Pro"
        assert updated.json()["created_at"] == body["created_at"]

        disabled = client.patch("/api/v1/mcp-servers/taxi-tools/disable")
        assert disabled.status_code == 200
        assert disabled.json()["enabled"] is False

        enabled = client.patch("/api/v1/mcp-servers/taxi-tools/enable")
        assert enabled.json()["enabled"] is True

        deleted = client.delete("/api/v1/mcp-servers/taxi-tools")
        assert deleted.status_code == 204
        assert client.get("/api/v1/mcp-servers/taxi-tools").status_code == 404

    def test_duplicate_is_conflict(self, client: TestClient) -> None:
        client.post("/api/v1/mcp-servers", json=MCP_PAYLOAD)
        response = client.post("/api/v1/mcp-servers", json=MCP_PAYLOAD)
        assert response.status_code == 409

    def test_get_unknown_is_not_found(self, client: TestClient) -> None:
        assert client.get("/api/v1/mcp-servers/missing").status_code == 404

    def test_enabled_filter_excludes_disabled(self, client: TestClient) -> None:
        client.post("/api/v1/mcp-servers", json=MCP_PAYLOAD)
        car_payload = {**MCP_PAYLOAD, "id": "car-tools", "name": "Car Tools", "enabled": False}
        client.post("/api/v1/mcp-servers", json=car_payload)

        active = client.get("/api/v1/mcp-servers", params={"enabled": True}).json()
        disabled = client.get("/api/v1/mcp-servers", params={"enabled": False}).json()
        assert [item["id"] for item in active] == ["taxi-tools"]
        assert [item["id"] for item in disabled] == ["car-tools"]

    def test_toggle_unknown_is_not_found(self, client: TestClient) -> None:
        assert client.patch("/api/v1/mcp-servers/missing/enable").status_code == 404


class TestAgentApi:
    def test_full_crud_flow(self, client: TestClient) -> None:
        created = client.post("/api/v1/agents", json=AGENT_PAYLOAD)
        assert created.status_code == 201
        body = created.json()
        assert body["id"] == "taxi_agent"
        assert body["config"] == {"region": "nyc"}
        assert body["policy"]["temperature"] == 0.0

        fetched = client.get("/api/v1/agents/taxi_agent")
        assert fetched.status_code == 200
        assert fetched.json()["capability"] == "taxi-search"

        updated = client.put(
            "/api/v1/agents/taxi_agent", json={"model": "gemini-flash", "capability": "taxi-book"}
        )
        assert updated.status_code == 200
        assert updated.json()["model"] == "gemini-flash"
        assert updated.json()["capability"] == "taxi-book"

        disabled = client.patch("/api/v1/agents/taxi_agent/disable")
        assert disabled.json()["enabled"] is False
        enabled = client.patch("/api/v1/agents/taxi_agent/enable")
        assert enabled.json()["enabled"] is True

        assert client.delete("/api/v1/agents/taxi_agent").status_code == 204
        assert client.get("/api/v1/agents/taxi_agent").status_code == 404

    def test_duplicate_is_conflict(self, client: TestClient) -> None:
        client.post("/api/v1/agents", json=AGENT_PAYLOAD)
        assert client.post("/api/v1/agents", json=AGENT_PAYLOAD).status_code == 409

    def test_policy_create_and_partial_update(self, client: TestClient) -> None:
        payload = {**AGENT_PAYLOAD, "policy": {"temperature": 0.7, "seed": 11}}
        created = client.post("/api/v1/agents", json=payload)
        assert created.status_code == 201
        assert created.json()["policy"] == {
            "temperature": 0.7,
            "seed": 11,
            "timeout_seconds": 60,
            "max_tool_calls": 20,
            "max_retries": 2,
            "max_iterations": 3,
        }

        updated = client.put(
            "/api/v1/agents/taxi_agent", json={"policy": {"temperature": 0.0}}
        )
        assert updated.status_code == 200
        assert updated.json()["policy"]["temperature"] == 0.0
        assert updated.json()["policy"]["seed"] == 11
        assert updated.json()["policy"]["timeout_seconds"] == 60

    def test_enabled_filter_excludes_disabled(self, client: TestClient) -> None:
        client.post("/api/v1/agents", json=AGENT_PAYLOAD)
        client.post(
            "/api/v1/agents",
            json={**AGENT_PAYLOAD, "id": "car_agent", "name": "Car Agent", "enabled": False},
        )
        active = client.get("/api/v1/agents", params={"enabled": True}).json()
        assert [item["id"] for item in active] == ["taxi_agent"]

    def test_health(self, client: TestClient) -> None:
        assert client.get("/health").json() == {"status": "ok", "registry": "ready"}