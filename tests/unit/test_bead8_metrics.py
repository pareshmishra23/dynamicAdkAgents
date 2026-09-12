import json
from dataclasses import replace

import pytest

from app.agents.factory import default_agent_factory
from app.agents.langgraph_engine import LangGraphOrchestrator
from app.metrics import (
    ESCALATION_STATUSES,
    collect_run,
    compare_metrics,
    export_metrics,
    load_metrics,
)
from app.models import AgentDefinition, RoutingResult, SelectedAgent
from app.registry.agent_registry import AgentRegistry
from app.registry.policy import PolicyAudit, PolicyEnforcer
from app.registry.resolver import AgentResolver
from app.solver.problems import BENCHMARK_PROBLEMS
from app.solver.runner import solve_problem
from app.tools.registry import default_tool_registry


def stub_dict(problem_id, status="completed", passed=True, escalation=False):
    return {
        "problem_id": problem_id,
        "title": "t",
        "status": status,
        "passed": passed,
        "duration_ms": 1.0,
        "iterations": 0,
        "tool_calls": 0,
        "escalation": escalation,
        "decided_agents": [],
    }


class TestCollectAndExport:
    def test_collect_deterministic_run(self):
        run = solve_problem(BENCHMARK_PROBLEMS[0])
        metric = collect_run(BENCHMARK_PROBLEMS[0], run)
        assert metric.passed is True
        assert metric.status == "completed"
        assert metric.escalation is False
        assert metric.tool_calls >= 0
        assert metric.decided_agents

    def test_export_and_reload_roundtrip(self, tmp_path):
        runs = [solve_problem(p) for p in BENCHMARK_PROBLEMS[:2]]
        path = tmp_path / "metrics.json"
        metrics = export_metrics(runs, path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert len(payload) == 2
        assert {m["problem_id"] for m in payload} == {m.problem_id for m in metrics}

    def test_escaped_status_collected_as_escalation(self):
        fake_status = sorted(ESCALATION_STATUSES)[0]
        run = solve_problem(BENCHMARK_PROBLEMS[0])
        run = run.__class__(
            problem=run.problem,
            decided_agents=run.decided_agents,
            rationale=run.rationale,
            result=replace(run.result, status=fake_status),
            duration_ms=run.duration_ms,
        )
        metric = collect_run(run.problem, run)
        assert metric.status == fake_status
        assert metric.escalation is True


class TestCompare:
    def test_detects_status_regression(self):
        current = [collect_run(BENCHMARK_PROBLEMS[0], solve_problem(BENCHMARK_PROBLEMS[0]))]
        gold = {"1": stub_dict("1", status="policy_violation")}
        report = compare_metrics(current, gold)
        assert report["regressions"]

    def test_clean_when_matching(self):
        run = solve_problem(BENCHMARK_PROBLEMS[0])
        metric = collect_run(BENCHMARK_PROBLEMS[0], run)
        gold = {"1": stub_dict("1", status="completed", passed=True, escalation=False)}
        report = compare_metrics([metric], gold)
        assert report["regressions"] == []

    def test_missing_problem_regression(self):
        report = compare_metrics([], {"9": stub_dict("9")})
        assert report["regressions"][0]["issue"] == "missing in current run"

    def test_load_missing_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_metrics(tmp_path / "nope.json")


class TestEscalationPath:
    def test_engine_policy_violation_is_escalation(self):
        rogue = AgentDefinition(
            id="rogue",
            version="v1",
            enabled=True,
            name="rogue",
            description="d",
            capabilities=("solve",),
            instructions="i",
            input_contract={},
            output_contract={"type": "object", "properties": {}},
            allowed_tools=("websearch",),
        )
        registry = AgentRegistry((rogue,))
        enforcer = PolicyEnforcer(default_tool_registry(), PolicyAudit())

        def factory(definition):
            return enforcer.wrap(definition, default_agent_factory(definition))

        resolver = AgentResolver(registry, factory)
        engine = LangGraphOrchestrator(resolver, max_iterations=2)
        result = engine.start(RoutingResult((SelectedAgent("rogue", "reason", "task"),)))
        assert result.status == "policy_violation"