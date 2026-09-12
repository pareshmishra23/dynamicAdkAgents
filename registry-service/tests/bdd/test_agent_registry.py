from __future__ import annotations

from pathlib import Path

from pytest_bdd import given, parsers, scenarios, then, when
scenarios(str(Path(__file__).parents[2] / "features" / "agent_registry.feature"))


def _register(state: dict, name: str, capability: str = "general", enabled: bool = True) -> None:
    payload = {
        "id": name,
        "name": name.replace("_", " ").title(),
        "description": f"Agent for {name}",
        "capability": capability,
        "model": "local-model",
        "enabled": enabled,
        "config": {},
    }
    state["last"] = state["client"].post("/api/v1/agents", json=payload)


@given("the agent registry is empty")
def agent_registry_is_empty(state: dict) -> None:
    response = state["client"].get("/api/v1/agents")
    assert response.status_code == 200
    assert response.json() == []


@given(parsers.parse('an agent "{name}" is registered'))
def agent_is_registered(state: dict, name: str) -> None:
    _register(state, name)


@given(parsers.parse('the agent "{name}" is registered and disabled'))
def agent_is_registered_and_disabled(state: dict, name: str) -> None:
    _register(state, name, enabled=False)


@when(parsers.parse('I register the agent "{name}" with capability "{capability}"'))
def register_agent(state: dict, name: str, capability: str) -> None:
    _register(state, name, capability=capability)


@when(parsers.parse('I register the agent "{name}" again'))
def register_agent_again(state: dict, name: str) -> None:
    _register(state, name)


@when(parsers.parse('I retrieve the agent "{name}"'))
def retrieve_agent(state: dict, name: str) -> None:
    state["last"] = state["client"].get(f"/api/v1/agents/{name}")


@when(parsers.parse('I disable the agent "{name}"'))
def disable_agent(state: dict, name: str) -> None:
    state["last"] = state["client"].patch(f"/api/v1/agents/{name}/disable")


@when(parsers.parse('I enable the agent "{name}"'))
def enable_agent(state: dict, name: str) -> None:
    state["last"] = state["client"].patch(f"/api/v1/agents/{name}/enable")


@when(parsers.parse('I delete the agent "{name}"'))
def delete_agent(state: dict, name: str) -> None:
    state["last"] = state["client"].delete(f"/api/v1/agents/{name}")


@then(parsers.parse('the agent "{name}" is registered'))
def agent_is_registered_check(state: dict, name: str) -> None:
    assert state["last"].status_code == 201
    assert state["last"].json()["id"] == name


@then(parsers.parse('the response contains the agent "{name}"'))
def response_contains_agent(state: dict, name: str) -> None:
    assert state["last"].status_code == 200
    assert state["last"].json()["id"] == name


@then(parsers.parse('the agent "{name}" is disabled'))
def agent_is_disabled(state: dict, name: str) -> None:
    assert state["last"].status_code == 200
    assert state["last"].json()["enabled"] is False


@then(parsers.parse('the agent "{name}" is enabled'))
def agent_is_enabled(state: dict, name: str) -> None:
    assert state["last"].status_code == 200
    assert state["last"].json()["enabled"] is True


@then(parsers.parse('the agent "{name}" is no longer registered'))
def agent_is_no_longer_registered(state: dict, name: str) -> None:
    assert state["last"].status_code == 204


@then("the duplicate registration is rejected with status 409")
def duplicate_agent_rejected(state: dict) -> None:
    assert state["last"].status_code == 409