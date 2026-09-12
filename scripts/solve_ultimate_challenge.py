import os
import time
from pathlib import Path

from app.agents.langgraph_engine import LangGraphOrchestrator
from app.agents.traces import ThinkTracer
from app.models import RoutingResult, SelectedAgent
from app.registry.agent_registry import AgentRegistry
from app.registry.resolver import AgentResolver
from app.solver.ultimate import ULTIMATE_CHALLENGE
from app.solver.ultimate_solver import (
    build_ultimate_factory,
    evaluate_ultimate,
    research_definition,
    trip_planner_definition,
)

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "docs" / "ULTIMATE_CHALLENGE_SOLVE.md"


def main() -> None:
    spec = ULTIMATE_CHALLENGE
    definitions = (research_definition(), trip_planner_definition())
    registry = AgentRegistry(definitions)
    trace = ThinkTracer()
    factory = build_ultimate_factory(spec, trace=trace)
    resolver = AgentResolver(registry, factory)
    routing = RoutingResult(
        (
            SelectedAgent("research_agent", "live data + grounding (BEAD 7)", "research the NY trip costs"),
            SelectedAgent("trip_planner", "assemble matrix + 2 options", "build cost matrix and two options"),
        )
    )
    engine = LangGraphOrchestrator(resolver, trace=trace, max_iterations=3)
    started = time.perf_counter()
    result = engine.start(routing, run_id=f"ultimate-{spec.id}")
    duration_ms = (time.perf_counter() - started) * 1000
    verdict = evaluate_ultimate(result.decision or "", spec)

    txt = [
        f"# Ultimate Challenge Solve — {spec.id}",
        "",
        f"- Status: **{result.status}** | duration {duration_ms:.0f} ms | iterations {result.iterations}",
        f"- Evaluated pass: **{verdict['passed']}** | cost-matrix present: {verdict['has_matrix']} | touring stops: {verdict['has_touring_stops']}",
        "- Per-option totals found:",
    ]
    for label, entry in verdict["options"].items():
        txt.append(f"  - {label}: USD={entry['usd_in_decision']} INR={entry['inr_in_decision']} found={entry['found']}")
    txt += ["", "## Pool decision", "", (result.decision or "").strip()]
    txt += ["", "## Trace snippet"]
    txt += ["```", *[f"{step}" for step in trace.steps[:24]], "```"]
    REPORT.write_text("\n".join(txt) + "\n", encoding="utf-8")
    print(f"status={result.status} passed={verdict['passed']} ({duration_ms:.0f}ms)")
    print(f"Report: {REPORT}")
    if result.status != "completed" or not verdict["passed"]:
        raise SystemExit(f"ultimate challenge did not pass: status={result.status} verdict={verdict['passed']}")


if __name__ == "__main__":
    main()