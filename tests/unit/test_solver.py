from __future__ import annotations

from app.solver.agents import make_solver_factory
from app.solver.planner import plan_agents
from app.solver.problems import BENCHMARK_PROBLEMS
from app.solver.runner import solve_problem


def test_planner_decides_pool_for_problem_1() -> None:
    plan = plan_agents(PROBLEM_1 := BENCHMARK_PROBLEMS[0])
    assert {p.definition.id for p in plan.agents} == {"graph_builder", "tour_engine", "route_validator"}
    assert "base pool of 3 agents" in plan.rationale


def test_problem_1_solves_triangle_route() -> None:
    run = solve_problem(BENCHMARK_PROBLEMS[0])
    assert run.result.status == "completed"
    assert run.passed()
    assert all(city in run.result.decision for city in ("A", "B", "C"))
    assert "45" in run.result.decision


def test_problem_2_solves_square_matrix() -> None:
    run = solve_problem(BENCHMARK_PROBLEMS[1])
    assert run.result.status == "completed"
    assert run.passed()
    assert all(city in run.result.decision for city in ("A", "B", "C", "D"))
    assert "40" in run.result.decision


def test_solver_agents_are_deterministic() -> None:
    from app.solver.planner import plan_agents

    factory = make_solver_factory(BENCHMARK_PROBLEMS[0])
    tour = [p for p in plan_agents(BENCHMARK_PROBLEMS[0]).agents if p.definition.id == "tour_engine"][0].definition
    first = factory(tour)("enumerate candidate loops")
    second = factory(tour)("enumerate candidate loops")
    assert first.recommendation == second.recommendation
    assert "A->B->C" in first.recommendation and "45" in first.recommendation