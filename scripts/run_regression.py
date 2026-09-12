import argparse
import json
from pathlib import Path

from app.agents.traces import ThinkTracer
from app.metrics import compare_metrics, export_metrics, load_metrics
from app.solver.problems import BENCHMARK_PROBLEMS
from app.solver.runner import solve_problem

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--golden", default=str(ROOT / "golden" / "metrics.json"))
    parser.add_argument("--trace-dir", default=str(ROOT / "logs" / "regression"))
    args = parser.parse_args()
    golden_path = Path(args.golden)
    trace_dir = Path(args.trace_dir)

    runs = []
    for problem in BENCHMARK_PROBLEMS:
        trace = ThinkTracer()
        run = solve_problem(problem, trace=trace)
        runs.append(run)
        trace_dir.mkdir(parents=True, exist_ok=True)
        (trace_dir / f"problem_{problem.id}.log").write_text(
            "\n".join(trace.steps) + "\n",
            encoding="utf-8",
        )

    metrics = export_metrics(runs, Path(ROOT) / "golden" / "replay_metrics.json")
    if not golden_path.exists():
        golden_path.parent.mkdir(parents=True, exist_ok=True)
        golden_path.write_text(
            json.dumps([m.to_dict() for m in metrics], indent=2), encoding="utf-8"
        )
        print(f"Baseline golden written to {golden_path} ({len(metrics)} problems)")
        return
    golden = load_metrics(golden_path)
    report = compare_metrics(metrics, golden)
    table = ["# Benchmark Regression Report", "", "| Problem | Status | Passed | Escalation | Duration (ms) |", "| --- | --- | --- | --- | --- |"]
    for metric in metrics:
        table.append(
            f"| {metric.problem_id} | {metric.status} | {metric.passed} | {metric.escalation} | {metric.duration_ms} |"
        )
    table.append("")
    regressions = report["regressions"]
    table.append(f"## Regressions: {len(regressions)}")
    for entry in regressions:
        table.append(f"- P{entry['problem_id']}: {entry['issue']} (gold={entry.get('gold')} current={entry.get('current')})")
    docs = ROOT / "docs" / "BENCHMARK_REGRESSION.md"
    docs.write_text("\n".join(table) + "\n", encoding="utf-8")
    total = len([m for m in metrics if m.passed])
    print(f"{total}/{len(metrics)} problems pass, regressions={len(regressions)}")
    print(f"Report: {docs}")


if __name__ == "__main__":
    main()