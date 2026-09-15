from __future__ import annotations

from fastapi.testclient import TestClient


def test_create_and_get_tool(client: TestClient) -> None:
    payload = {
        "tool_id": "matrix_build",
        "name": "Matrix Builder",
        "description": "Constructs coordinate cost matrix",
        "capability": "graph_analysis",
        "provider": "solver-mcp",
        "enabled": True,
        "config": {"metric": "euclidean"},
    }
    resp = client.post("/api/v1/tools", json=payload)
    assert resp.status_code == 201
    created = resp.json()
    assert created["tool_id"] == "matrix_build"
    assert created["capability"] == "graph_analysis"
    assert created["provider"] == "solver-mcp"
    assert created["enabled"] is True

    get_resp = client.get("/api/v1/tools/matrix_build")
    assert get_resp.status_code == 200
    assert get_resp.json()["tool_id"] == "matrix_build"


def test_duplicate_tool_rejected(client: TestClient) -> None:
    payload = {
        "tool_id": "tour_enum",
        "name": "Tour Enumerator",
        "capability": "route_optimization",
        "provider": "solver-mcp",
    }
    first = client.post("/api/v1/tools", json=payload)
    assert first.status_code == 201

    second = client.post("/api/v1/tools", json=payload)
    assert second.status_code == 409
    assert "already registered" in second.json()["detail"]


def test_list_tools_filtering(client: TestClient) -> None:
    client.post(
        "/api/v1/tools",
        json={
            "tool_id": "t1",
            "name": "Tool 1",
            "capability": "route_optimization",
            "provider": "p1",
            "enabled": True,
        },
    )
    client.post(
        "/api/v1/tools",
        json={
            "tool_id": "t2",
            "name": "Tool 2",
            "capability": "constraint_reasoning",
            "provider": "p1",
            "enabled": False,
        },
    )

    all_tools = client.get("/api/v1/tools").json()
    assert len(all_tools) == 2

    enabled_only = client.get("/api/v1/tools?enabled=true").json()
    assert len(enabled_only) == 1
    assert enabled_only[0]["tool_id"] == "t1"

    by_cap = client.get("/api/v1/tools?capability=constraint_reasoning").json()
    assert len(by_cap) == 1
    assert by_cap[0]["tool_id"] == "t2"


def test_enable_disable_tool(client: TestClient) -> None:
    client.post(
        "/api/v1/tools",
        json={
            "tool_id": "t_toggle",
            "name": "Toggle Tool",
            "capability": "testing",
            "enabled": True,
        },
    )
    # Disable
    dis = client.patch("/api/v1/tools/t_toggle/disable")
    assert dis.status_code == 200
    assert dis.json()["enabled"] is False

    # Enable
    en = client.patch("/api/v1/tools/t_toggle/enable")
    assert en.status_code == 200
    assert en.json()["enabled"] is True


def test_update_and_delete_tool(client: TestClient) -> None:
    client.post(
        "/api/v1/tools",
        json={
            "tool_id": "t_up",
            "name": "Old Name",
            "capability": "testing",
        },
    )
    up = client.put("/api/v1/tools/t_up", json={"name": "New Name", "description": "Updated desc"})
    assert up.status_code == 200
    assert up.json()["name"] == "New Name"
    assert up.json()["description"] == "Updated desc"

    dele = client.delete("/api/v1/tools/t_up")
    assert dele.status_code == 204

    assert client.get("/api/v1/tools/t_up").status_code == 404
