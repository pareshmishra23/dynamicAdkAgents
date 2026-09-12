import sys

from app.agents.traces import ThinkTracer
from app.solver.problems import BENCHMARK_PROBLEMS
from app.solver.runner import solve_problem


def main() -> None:
    index = int(sys.argv[1]) - 1 if len(sys.argv) > 1 and sys.argv[1].isdigit() else 0
    problem = BENCHMARK_PROBLEMS[index]
    print(f"PROBLEM {problem.id}: {problem.title}")
    print(f"Cities: {', '.join(problem.cities)} | Edges: "
          + ", ".join(f"{e.a}-{e.b}={e.cost}" for e in problem.edges)
          + (f" | expected: {'->'.join(problem.expected)} total {problem.expected_cost}" if problem.expected else "")
          + (" | expected: impossible" if problem.impossible else ""))
    print("=" * 78)

    run = solve_problem(problem, trace=ThinkTracer())
    print("=" * 78)
    print("FINAL DECISION:", run.result.decision)
    print(f"STATUS: {run.result.status} | agents created: {len(run.decided_agents)} "
          f"{list(run.decided_agents)} | iterations: {run.result.iterations}")
    print(f"EXPECTATION: {'PASS' if run.passed() else 'FAIL'}")


if __name__ == "__main__":
    main()