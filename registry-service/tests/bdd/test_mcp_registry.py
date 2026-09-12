from __future__ import annotations

from pathlib import Path

from pytest_bdd import given, parsers, scenarios, then, when
scenarios(str(Path(__file__).parents[2] / "features" / "mcp_registry.feature"))


def _register(state: dict, name: str, endpoint: str | None = None, enabled: bool = True) -> None:
    payload = {
        "id": name,
        "name": name.replace("-", " ").title(),
        "description": f"MCP server for {name}",
        "endpoint": endpoint or f"stdio://{name}",
        "transport": "stdio",
        "enabled": enabled,
        "version": "1.0.0",
    }
    state["last"] = state["client"].post("/api/v1/mcp-servers", json=payload)


@given("the MCP registry is empty")
def mcp_registry_is_empty(state: dict) -> None:
    response = state["client"].get("/api/v1/mcp-servers")
    assert response.status_code == 200
    assert response.json() == []


@given(parsers.parse('an MCP server "{name}" is registered'))
def mcp_server_is_registered(state: dict, name: str) -> None:
    _register(state, name)


@given(parsers.parse('the MCP server "{name}" is registered and disabled'))
def mcp_server_is_registered_and_disabled(state: dict, name: str) -> None:
    _register(state, name, enabled=False)


@when(parsers.parse('I register the MCP server "{name}" with endpoint "{endpoint}"'))
def register_mcp_server(state: dict, name: str, endpoint: str) -> None:
    _register(state, name, endpoint=endpoint)


@when(parsers.parse('I register the MCP server "{name}" again'))
def register_mcp_server_again(state: dict, name: str) -> None:
    _register(state, name)


@when(parsers.parse('I retrieve the MCP server "{name}"'))
def retrieve_mcp_server(state: dict, name: str) -> None:
    state["last"] = state["client"].get(f"/api/v1/mcp-servers/{name}")


@when(parsers.parse('I disable the MCP server "{name}"'))
def disable_mcp_server(state: dict, name: str) -> None:
    state["last"] = state["client"].patch(f"/api/v1/mcp-servers/{name}/disable")


@when(parsers.parse('I enable the MCP server "{name}"'))
def enable_mcp_server(state: dict, name: str) -> None:
    state["last"] = state["client"].patch(f"/api/v1/mcp-servers/{name}/enable")


@when(parsers.parse('I delete the MCP server "{name}"'))
def delete_mcp_server(state: dict, name: str) -> None:
    state["last"] = state["client"].delete(f"/api/v1/mcp-servers/{name}")


@when("I list enabled MCP servers")
def list_enabled_mcp_servers(state: dict) -> None:
    state["last"] = state["client"].get("/api/v1/mcp-servers", params={"enabled": True})


@then(parsers.parse('the server "{name}" is registered'))
def mcp_server_is_registered_check(state: dict, name: str) -> None:
    assert state["last"].status_code == 201
    assert state["last"].json()["id"] == name


@then("the registry contains 1 servers")
def registry_contains_one(state: dict) -> None:
    response = state["client"].get("/api/v1/mcp-servers")
    assert len(response.json()) == 1


@then(parsers.parse('the response contains the server "{name}"'))
def response_contains_mcp_server(state: dict, name: str) -> None:
    assert state["last"].status_code == 200
    assert state["last"].json()["id"] == name


@then(parsers.parse('the server "{name}" is disabled'))
def mcp_server_is_disabled(state: dict, name: str) -> None:
    assert state["last"].status_code == 200
    assert state["last"].json()["enabled"] is False


@then(parsers.parse('the server "{name}" is enabled'))
def mcp_server_is_enabled(state: dict, name: str) -> None:
    assert state["last"].status_code == 200
    assert state["last"].json()["enabled"] is True


@then(parsers.parse('the server "{name}" is no longer registered'))
def mcp_server_is_no_longer_registered(state: dict, name: str) -> None:
    assert state["last"].status_code == 204


@then("the duplicate registration is rejected with status 409")
def duplicate_registration_rejected(state: dict) -> None:
    assert state["last"].status_code == 409


@then(parsers.parse('only the server "{name}" is returned'))
def only_mcp_server_returned(state: dict, name: str) -> None:
    assert [item["id"] for item in state["last"].json()] == [name]