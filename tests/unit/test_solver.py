from __future__ import annotations

from app.solver.agents import make_solver_factory
from app.solver.planner import plan_agents
from app.solver.problems import BENCHMARK_PROBLEMS, PROBLEM_7, PROBLEM_8, PROBLEM_9, PROBLEM_10
from app.solver.runner import solve_problem


def test_planner_decides_pool_for_problem_1() -> None:
    plan = plan_agents(BENCHMARK_PROBLEMS[0])
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


def test_problem_3_solves_linear_highway() -> None:
    run = solve_problem(BENCHMARK_PROBLEMS[2])
    assert run.passed()
    assert "60" in run.result.decision


def test_problem_4_uses_clockwise_direction() -> None:
    run = solve_problem(BENCHMARK_PROBLEMS[3])
    assert run.passed()
    assert "25" in run.result.decision


def test_problem_5_honors_first_stop_constraint() -> None:
    run = solve_problem(BENCHMARK_PROBLEMS[4])
    assert run.passed()
    assert "60" in run.result.decision
    decision = run.result.decision
    assert "A->C" in decision


def test_problem_6_hub_spoke() -> None:
    run = solve_problem(BENCHMARK_PROBLEMS[5])
    assert run.passed()
    assert "110" in run.result.decision


def test_problem_7_15_city_uses_heuristic_pool() -> None:
    plan = plan_agents(PROBLEM_7)
    assert {p.definition.id for p in plan.agents} == {
        "graph_builder", "tour_engine", "route_validator", "optimizer",
    }
    run = solve_problem(PROBLEM_7)
    assert run.result.status == "completed"
    assert run.passed()


def test_problem_8_vrp_pool_and_feasible_split() -> None:
    plan = plan_agents(PROBLEM_8)
    assert {p.definition.id for p in plan.agents} == {"vrp_splitter", "vrp_validator"}
    run = solve_problem(PROBLEM_8)
    assert run.result.status == "completed"
    assert run.passed()


def test_problem_9_disconnected_island_abstains() -> None:
    run = solve_problem(PROBLEM_9)
    assert run.result.status == "completed"
    assert run.passed()
    assert "no Hamiltonian cycle exists" in run.result.decision


def test_problem_10_circular_dependency_abstains() -> None:
    plan = plan_agents(PROBLEM_10)
    assert {p.definition.id for p in plan.agents} == {"dependency_checker", "order_reviewer"}
    run = solve_problem(PROBLEM_10)
    assert run.result.status == "completed"
    assert run.passed()
    assert "circular dependency" in run.result.decision


def test_solver_agents_are_deterministic() -> None:
    from app.solver.planner import plan_agents

    factory = make_solver_factory(BENCHMARK_PROBLEMS[0])
    tour = [p for p in plan_agents(BENCHMARK_PROBLEMS[0]).agents if p.definition.id == "tour_engine"][0].definition
    first = factory(tour)("enumerate candidate loops")
    second = factory(tour)("enumerate candidate loops")
    assert first.recommendation == second.recommendation
    assert "A->B->C" in first.recommendation and "45" in first.recommendation