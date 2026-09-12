from pathlib import Path

from app.agents.factory import default_agent_factory
from app.agents.orchestrator import BoundedRefiner, Critique, Orchestrator
from app.agents.router import Router
from app.config.loader import load_agent_definitions
from app.registry.agent_registry import AgentRegistry
from app.registry.resolver import AgentResolver

ROOT = Path(__file__).parents[2]


def setup_orchestrator():
    registry = AgentRegistry(load_agent_definitions(ROOT / "config/agents.yaml"))
    resolver = AgentResolver(registry, default_agent_factory)
    routing = Router(registry).route("sightseeing adventure taxi")
    return Orchestrator(resolver), routing


def test_parallel_execution_exposes_only_selected_agents_as_tools():
    orchestrator, routing = setup_orchestrator()
    tools = orchestrator.selected_tools(routing)
    result = orchestrator.run(routing, parallel=True)
    assert {tool.agent_id for tool in tools} == {item.agent_id for item in routing.selected_agents}
    assert len(result.specialist_results) == 3
    assert result.trace[-2] == "parallel"
    assert result.status == "completed"


def test_sequential_execution_is_supported():
    orchestrator, routing = setup_orchestrator()
    result = orchestrator.run(routing, parallel=False)
    assert len(result.specialist_results) == 3
    assert result.trace[-2] == "sequential"
    assert result.final_decision.startswith("Integrated decision:")


def test_refiner_revises_then_completes():
    calls = []

    def critic(proposal):
        calls.append(proposal)
        return Critique(valid=len(calls) == 2, issue="duration exceeds three days", question="Which activity should be shortened?")

    refiner = BoundedRefiner(critic, lambda proposal, critique: proposal + " [shortened]", max_iterations=3)
    proposal, iterations, status = refiner.run("three-day plan")
    assert proposal.endswith("[shortened]")
    assert iterations == 2
    assert status == "completed"


def test_refiner_abstains_after_maximum_iterations():
    refiner = BoundedRefiner(
        lambda proposal: Critique(False, "unresolved", "What should change?"),
        lambda proposal, critique: proposal + "*",
        max_iterations=3,
    )
    proposal, iterations, status = refiner.run("plan")
    assert proposal == "plan***"
    assert iterations == 3
    assert status == "abstain_human_review"
