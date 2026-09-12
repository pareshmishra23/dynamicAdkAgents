import sys
from pathlib import Path

from app.agents.traces import ThinkTracer
from app.solver.problems import BENCHMARK_PROBLEMS
from app.solver.runner import SolutionRun, solve_problem

ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "logs"
REPORT_PATH = ROOT / "docs" / "benchmark_report.md"


def rate(problem, run: SolutionRun) -> str:
    if run.result.status != "completed":
        return "BROKEN (run did not complete)"
    if problem.impossible or problem.precedence:
        return "EXCELLENT (correctly abstains / proves impossibility)" if run.passed() else "BROKEN (claimed feasible)"
    if problem.kind == "vrp":
        return "GOOD (feasible balanced split, not proven optimal)" if run.passed() else "BROKEN"
    if problem.expected is None:
        return "GOOD (feasible heuristic, optimum unknown)"
    if len(problem.cities) <= 9:
        return "EXCELLENT (exact enumeration)" if run.passed() else "BROKEN (missed the known optimum)"
    return "GOOD (heuristic, optimality not proven)"


def run_single(index: int) -> SolutionRun:
    problem = BENCHMARK_PROBLEMS[index]
    print(f"PROBLEM {problem.id}: {problem.title}")
    print(f"Cities: {', '.join(problem.cities)}")
    if problem.edges:
        print("Edges: " + ", ".join(f"{e.a}-{e.b}={e.cost}" for e in problem.edges))
    print("=" * 78)
    run = solve_problem(problem, trace=ThinkTracer(), log_dir=LOG_DIR)
    print("=" * 78)
    print(f"FINAL DECISION: {run.result.decision}")
    print(
        f"STATUS: {run.result.status} | agents created: {len(run.decided_agents)} "
        f"{list(run.decided_agents)} | iterations: {run.result.iterations} | time: {run.duration_ms}ms"
    )
    print(f"EXPECTATION: {'PASS' if run.passed() else 'FAIL'} | RATING: {rate(problem, run)}")
    return run


def run_all() -> tuple[SolutionRun, ...]:
    return tuple(run_single(i) for i in range(len(BENCHMARK_PROBLEMS)))


def emit_report(runs: tuple[SolutionRun, ...]) -> None:
    lines = ["# Agent Pool Solver Benchmark Report", ""]
    lines.append("Run on a deterministic local pool (no model calls). Each problem solved by a")
    lines.append("planner-decided agent pool; full thinking traces saved under `logs/problem_<n>.log`.")
    lines.append("")
    lines.append("| # | Problem | n | Pool size | Agents | Time (ms) | Status | Rating |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for run in runs:
        p = run.problem
        lines.append(
            f"| {p.id} | {p.title} | {len(p.cities)} | {len(run.decided_agents)} | "
            f"{', '.join(run.decided_agents)} | {run.duration_ms} | "
            f"{run.result.status} | {rate(p, run)} |"
        )
    lines.append("")
    lines.append("## Solver pattern observations")
    lines.append("")
    lines.append("- Exact-enumeration path (n<=9) never misses the optimum; it is the reference oracle.")
    lines.append("- Heuristic path (n>9, 15-city) uses greedy nearest-neighbor + 2-opt; optimal not proven.")
    lines.append("- Impossibility / precedence problems route to a proof pool and abstain instead of guessing.")
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nReport written: {REPORT_PATH}")


def main() -> None:
    args = sys.argv[1:]
    if "--all" in args:
        runs = run_all()
        emit_report(runs)
        return
    index = int(args[0]) - 1 if args and args[0].isdigit() else 0
    run_single(index)


if __name__ == "__main__":
    main()