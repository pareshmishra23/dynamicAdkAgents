from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

from app.solver.runner import SolutionRun

ESCALATION_STATUSES = frozenset(
    {"abstain_human_review", "no_agents_authorized", "policy_violation"}
)


@dataclass
class RunMetric:
    problem_id: str
    title: str
    status: str
    passed: bool
    duration_ms: float
    iterations: int
    tool_calls: int
    escalation: bool
    decided_agents: list[str]
    decided_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)


def collect_run(problem, run: SolutionRun) -> RunMetric:
    tool_calls = sum(
        int(result.metadata.get("tool_calls", 0)) for result in run.result.results
    )
    return RunMetric(
        problem_id=problem.id,
        title=problem.title,
        status=run.result.status,
        passed=run.passed(),
        duration_ms=run.duration_ms,
        iterations=run.result.iterations,
        tool_calls=tool_calls,
        escalation=run.result.status in ESCALATION_STATUSES,
        decided_agents=list(run.decided_agents),
    )


def export_metrics(runs: Iterable[SolutionRun], path: Path) -> list[RunMetric]:
    metrics = [collect_run(run.problem, run) for run in runs]
    payload = [metric.to_dict() for metric in metrics]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return metrics


def load_metrics(path: Path) -> dict[str, dict]:
    if not path.exists():
        raise FileNotFoundError(f"no golden metrics at {path}")
    return {item["problem_id"]: item for item in json.loads(path.read_text(encoding="utf-8"))}


def compare_metrics(current: Iterable[RunMetric], golden: dict[str, dict]) -> dict:
    regressions: list[dict] = []
    current_map = {metric.problem_id: metric for metric in current}
    for problem_id, gold in golden.items():
        metric = current_map.get(problem_id)
        if metric is None:
            regressions.append({"problem_id": problem_id, "issue": "missing in current run"})
            continue
        if metric.status != gold["status"]:
            regressions.append(
                {
                    "problem_id": problem_id,
                    "issue": "status change",
                    "gold": gold["status"],
                    "current": metric.status,
                }
            )
        if metric.passed != gold["passed"]:
            regressions.append(
                {
                    "problem_id": problem_id,
                    "issue": "pass regression",
                    "gold": gold["passed"],
                    "current": metric.passed,
                }
            )
        if gold.get("escalation") is not None and bool(metric.escalation) != bool(gold["escalation"]):
            regressions.append(
                {
                    "problem_id": problem_id,
                    "issue": "escalation drift",
                    "gold": gold["escalation"],
                    "current": metric.escalation,
                }
            )
    return {"regressions": regressions}