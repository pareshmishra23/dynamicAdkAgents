import os

from app.solver.ultimate import ULTIMATE_CHALLENGE
from app.solver.ultimate_solver import (
    build_ultimate_factory,
    evaluate_ultimate,
    golden_decision,
    research_definition,
    trip_planner_definition,
)
from app.solver.planner import plan_agents  # noqa: F401


class TestGoldenReference:
    def test_golden_decision_passes_evaluator(self):
        decision = golden_decision(ULTIMATE_CHALLENGE)
        verdict = evaluate_ultimate(decision, ULTIMATE_CHALLENGE)
        assert verdict["passed"] is True
        assert verdict["has_matrix"] is True
        assert verdict["has_touring_stops"] is True
        assert all(entry["found"] for entry in verdict["options"].values())

    def test_wrong_totals_miss(self):
        decision = golden_decision(ULTIMATE_CHALLENGE).replace("1705", "9999")
        verdict = evaluate_ultimate(decision, ULTIMATE_CHALLENGE)
        assert verdict["passed"] is False
        assert verdict["options"]["Option 1: Lean Budget"]["found"] is False

    def test_missing_touring_stops_miss(self):
        decision = golden_decision(ULTIMATE_CHALLENGE).replace("Times Square", "Kremlin")
        verdict = evaluate_ultimate(decision, ULTIMATE_CHALLENGE)
        assert verdict["passed"] is False


class TestPoolFactory:
    def test_deterministic_default_factory(self, monkeypatch):
        monkeypatch.delenv("SOLVER_ADAPTER", raising=False)
        factory = build_ultimate_factory(ULTIMATE_CHALLENGE)
        planner = factory(trip_planner_definition())
        result = planner("build options")
        assert result.status == "completed"
        assert "1705" in result.recommendation

    def test_llm_gate_returns_live_adapter(self, monkeypatch):
        monkeypatch.setenv("SOLVER_ADAPTER", "llm")
        monkeypatch.setenv("LLM_BASE_URL", "http://localhost:1/v1")
        monkeypatch.setenv("LLM_MODEL", "fake")
        factory = build_ultimate_factory(ULTIMATE_CHALLENGE)
        research = factory(research_definition())
        assert research is not None


class TestResearchGrants:
    def test_research_agent_has_web_grants(self):
        definition = research_definition()
        assert set(definition.allowed_tools) == {"websearch", "webfetch"}
        from app.tools.registry import default_tool_registry

        registry = default_tool_registry()
        assert registry.allowed_for("websearch", "research_agent")


class TestLiveSolveIntegration:
    def test_offline_pool_solve_passes(self, monkeypatch):
        for var in ("SOLVER_ADAPTER", "LLM_BASE_URL", "LLM_MODEL", "LLM_API_KEY"):
            monkeypatch.delenv(var, raising=False)
        from app.agents.langgraph_engine import LangGraphOrchestrator
        from app.models import RoutingResult, SelectedAgent
        from app.registry.agent_registry import AgentRegistry
        from app.registry.resolver import AgentResolver

        definitions = (research_definition(), trip_planner_definition())
        registry = AgentRegistry(definitions)
        resolver = AgentResolver(registry, build_ultimate_factory(ULTIMATE_CHALLENGE))
        engine = LangGraphOrchestrator(resolver, max_iterations=3)
        result = engine.start(
            RoutingResult(
                (
                    SelectedAgent("research_agent", "r", "research"),
                    SelectedAgent("trip_planner", "p", "plan"),
                )
            )
        )
        assert result.status == "completed"
        assert evaluate_ultimate(result.decision or "", ULTIMATE_CHALLENGE)["passed"]