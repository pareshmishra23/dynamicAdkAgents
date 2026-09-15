from __future__ import annotations

from fastapi.testclient import TestClient


def test_list_benchmark_problems(client: TestClient) -> None:
    resp = client.get("/api/v1/benchmark-problems")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 10
    assert data[0]["id"] == "1"
    assert "Triangle" in data[0]["title"]


def test_overview_endpoint(client: TestClient) -> None:
    # Register an agent, tool, and MCP server
    client.post(
        "/api/v1/mcp-servers",
        json={
            "id": "mcp-solver",
            "name": "MCP Solver",
            "endpoint": "http://localhost:7101",
            "transport": "http",
        },
    )
    client.post(
        "/api/v1/tools",
        json={
            "tool_id": "tool-tsp",
            "name": "TSP Tool",
            "capability": "route_optimization",
            "provider": "mcp-solver",
        },
    )
    client.post(
        "/api/v1/agents",
        json={
            "id": "route-optimizer",
            "name": "Route Optimizer",
            "capability": "route_optimization",
            "model": "gemini-flash-latest",
        },
    )

    resp = client.get("/api/v1/overview")
    assert resp.status_code == 200
    overview = resp.json()
    assert overview["agents"]["total"] >= 1
    assert overview["mcp_servers"]["total"] >= 1
    assert overview["tools"]["total"] >= 1
    assert len(overview["relationships"]) >= 1


def test_execute_problem_1_optimal(client: TestClient) -> None:
    client.post(
        "/api/v1/agents",
        json={
            "id": "route-optimizer",
            "name": "Route Optimizer",
            "capability": "route_optimization",
            "model": "gemini-flash-latest",
        },
    )
    resp = client.post("/api/v1/execute", json={"problem_id": "1"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["guardrail_state"] == "OPTIMAL"
    assert data["guardrail_valid"] is True
    assert "45" in data["final_decision"]
    assert "route-optimizer" in data["scoped_agents"]
    assert data["trace"][-1] == "orchestrator_decision"


def test_execute_problem_9_impossible_abstains(client: TestClient) -> None:
    client.post(
        "/api/v1/agents",
        json={
            "id": "route-optimizer",
            "name": "Route Optimizer",
            "capability": "route_optimization",
            "model": "gemini-flash-latest",
        },
    )
    resp = client.post("/api/v1/execute", json={"problem_id": "9"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed_abstained"
    assert data["guardrail_state"] == "IMPOSSIBLE"
    assert data["guardrail_valid"] is False
    assert "ABSTAINED" in data["final_decision"]


def test_execute_disabled_agent_rejected(client: TestClient) -> None:
    client.post(
        "/api/v1/agents",
        json={
            "id": "route-optimizer",
            "name": "Route Optimizer",
            "capability": "route_optimization",
            "model": "gemini-flash-latest",
        },
    )
    # Disable the agent
    client.patch("/api/v1/agents/route-optimizer/disable")

    # Execution should now be rejected
    resp = client.post("/api/v1/execute", json={"problem_id": "1"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "rejected"
    assert "DISABLED" in data["guardrail_reason"]
    assert "REJECTED" in data["final_decision"]
