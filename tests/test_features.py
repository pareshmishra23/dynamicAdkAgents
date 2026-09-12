from pathlib import Path

import pytest
from pytest_bdd import given, scenarios, then, when

from app.agents.factory import default_agent_factory
from app.agents.orchestrator import BoundedRefiner, Critique, Orchestrator
from app.agents.router import Router, RoutingError
from app.config.loader import load_agent_definitions
from app.registry.agent_registry import AgentRegistry
from app.registry.resolver import AgentResolver

ROOT = Path(__file__).parents[1]
scenarios(str(ROOT / "features/dynamic_agent_routing.feature"))
scenarios(str(ROOT / "features/agent_orchestration.feature"))
scenarios(str(ROOT / "features/critic_refinement.feature"))


@pytest.fixture
def state():
    registry = AgentRegistry(load_agent_definitions(ROOT / "config/agents.yaml"))
    return {"registry": registry}


@given("the agent registry contains the five travel specialist agents")
def registry_has_five(state):
    assert len(state["registry"].list_enabled()) == 5


@when("the user requests sightseeing, adventure, car rental, taxi and social visits")
def route_trip(state):
    state["routing"] = Router(state["registry"]).route(
        "sightseeing adventure car rental taxi friends"
    )


@then("the router selects the required specialist agents")
def selected_required(state):
    assert {item.agent_id for item in state["routing"].selected_agents} == {
        "sightseeing_agent", "adventure_agent", "car_rental_agent", "taxi_agent", "friend_relative_agent"
    }


@then("the orchestrator receives only those selected agents")
def only_selected(state):
    orchestrator = Orchestrator(AgentResolver(state["registry"], default_agent_factory))
    assert {tool.agent_id for tool in orchestrator.selected_tools(state["routing"])} == {
        item.agent_id for item in state["routing"].selected_agents
    }


@given('the agent registry does not contain "banking_magic_agent"')
def no_unknown(state):
    assert not state["registry"].contains("banking_magic_agent")


@when('the router selects "banking_magic_agent"')
def route_unknown(state):
    with pytest.raises(RoutingError):
        Router(state["registry"]).route("request", selected_agent_ids=["banking_magic_agent"])
    state["rejected"] = True


@then("the routing request is rejected")
def rejected(state):
    assert state["rejected"] is True


@then("the unknown agent is not executed")
def unknown_not_executed(state):
    assert not state["registry"].contains("banking_magic_agent")


@given("the router selected sightseeing, adventure and taxi agents")
def selected_three(state):
    state["routing"] = Router(state["registry"]).route("request", selected_agent_ids=["sightseeing_agent", "adventure_agent", "taxi_agent"])


@when("the orchestrator executes the request in parallel")
def execute_parallel(state):
    state["result"] = Orchestrator(AgentResolver(state["registry"], default_agent_factory)).run(state["routing"])


@then("each selected agent is exposed as an agent-as-a-tool")
def selected_as_tools(state):
    assert state["result"].trace[2] == "agent_as_tool"
    assert len(state["result"].specialist_results) == 3


@then("the orchestrator integrates all specialist results")
def integrated(state):
    assert state["result"].final_decision.startswith("Integrated decision:")


@given("specialist results are available")
def results_available(state):
    state["routing"] = Router(state["registry"]).route("request", selected_agent_ids=["taxi_agent"])


@when("the orchestrator runs sequential integration")
def execute_sequential(state):
    state["result"] = Orchestrator(AgentResolver(state["registry"], default_agent_factory)).run(state["routing"], parallel=False)


@then("the final decision owner is the orchestrator")
def decision_owner(state):
    assert state["result"].trace[-1] == "orchestrator"


@given("the planner produced a proposal violating a three-day constraint")
def violating_proposal(state):
    state["proposal"] = "three-day plan with too many activities"


@when("the critic reviews the proposal")
def critic_reviews(state):
    state["refiner"] = BoundedRefiner(
        lambda proposal: Critique(False, "duration exceeds three days", "Which activity should be shortened?"),
        lambda proposal, critique: proposal + " [shortened]",
        max_iterations=1,
    )
    state["revised"], _, _ = state["refiner"].run(state["proposal"])
    state["critique_question"] = "Which activity should be shortened?"


@then("the critic produces a specific question")
def specific_question(state):
    assert state["critique_question"]


@then("the refiner produces a revised proposal")
def revised_proposal(state):
    assert state["revised"].endswith("[shortened]")


@given("the critic keeps finding an unresolved issue")
def unresolved(state):
    state["refiner"] = BoundedRefiner(
        lambda proposal: Critique(False, "unresolved", "What should change?"),
        lambda proposal, critique: proposal + "*",
        max_iterations=3,
    )


@when("the refinement loop reaches three iterations")
def reaches_limit(state):
    state["refinement"] = state["refiner"].run("plan")


@then("the workflow abstains and requests human review")
def abstains(state):
    assert state["refinement"][2] == "abstain_human_review"
