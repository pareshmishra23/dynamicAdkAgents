from pathlib import Path

from app.agents.factory import default_agent_factory
from app.agents.orchestrator import Orchestrator
from app.agents.router import Router
from app.config.loader import load_agent_definitions
from app.registry.agent_registry import AgentRegistry
from app.registry.resolver import AgentResolver


def main() -> None:
    root = Path(__file__).parents[1]
    registry = AgentRegistry(load_agent_definitions(root / "config/agents.yaml"))
    request = (
        "I am going to New York for 3 days. I want adventure activities and sightseeing. "
        "I will rent a car, need taxis, and want to visit friends and relatives."
    )
    routing = Router(registry).route(request, selected_agent_ids=[
        "sightseeing_agent", "adventure_agent", "car_rental_agent", "taxi_agent", "friend_relative_agent"
    ])
    result = Orchestrator(AgentResolver(registry, default_agent_factory)).run(routing)
    print("Router selected:")
    for item in routing.selected_agents:
        print(f"  - {item.agent_id}")
    print("Execution trace:")
    print("  " + " -> ".join(result.trace))
    print("Final plan:")
    print(result.final_decision)


if __name__ == "__main__":
    main()
