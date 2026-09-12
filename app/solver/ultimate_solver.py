from __future__ import annotations

import json
import os
from dataclasses import replace
from typing import Callable

from app.agents.adapter import LlmAgent
from app.models import AgentDefinition, AgentResult
from app.solver.llm import LlmConfig, chat
from app.solver.ultimate import UltimateChallengeSpec
from app.tools.web import granted_tools

ULTIMATE_SYSTEM = (
    "You are the ultimate-challenge trip planner (New York, 7 nights from Bengaluru). "
    "Given the spec below, output a COST MATRIX and exactly two solution options. For each "
    "option state the line items, then a TOTAL line with the exact plain integers from the "
    "spec (no commas, no currency symbols, e.g. TOTAL USD= 1705 and INR= 145000). Write numbers "
    "as plain digits. Also restate the 2-day touring plan and one cheap dinner place near the hotel."
)


def spec_payload(spec: UltimateChallengeSpec) -> dict:
    return {
        "id": spec.id,
        "origin": spec.origin,
        "destination_city": spec.destination_city,
        "nights": spec.nights,
        "hotel": spec.hotel,
        "office": spec.office,
        "booking_note": spec.search_reasoning_note,
        "options": [
            {
                "label": option.label,
                "lines": [
                    {"category": item.category, "detail": item.detail, "usd": item.usd, "inr": item.inr}
                    for item in option.items
                ],
                "total_usd": option.total_usd,
                "total_inr": option.total_inr,
            }
            for option in spec.options
        ],
        "touring_plan": [{"time": stop.time, "place": stop.place, "note": stop.note} for stop in spec.touring_plan],
        "dining_near_hotel": [
            {"name": d.name, "cuisine": d.cuisine, "price": d.price, "distance": d.distance}
            for d in spec.dining_near_hotel
        ],
    }


def research_definition() -> AgentDefinition:
    return AgentDefinition(
        id="research_agent",
        version="v1",
        enabled=True,
        name="NY Trip Researcher",
        description="live web research for the ultimate challenge (BEAD 7 grants)",
        capabilities=("research",),
        instructions="fetch and summarize live prices for the NY trip",
        input_contract={},
        output_contract={"type": "object", "properties": {}},
        allowed_tools=("websearch", "webfetch"),
        model=os.environ.get("LLM_MODEL", ""),
    )


def trip_planner_definition() -> AgentDefinition:
    return AgentDefinition(
        id="trip_planner",
        version="v1",
        enabled=True,
        name="Trip Planner",
        description="builds the cost matrix and two options for the NY trip",
        capabilities=("plan",),
        instructions="produce cost matrix and two solution options",
        input_contract={},
        output_contract={"type": "object", "properties": {}},
    )


def golden_decision(spec: UltimateChallengeSpec) -> str:
    lines = [
        f"Ultimate Challenge decision for {spec.title}",
        "",
        "COST MATRIX",
    ]
    for option in spec.options:
        lines.append(f"--- {option.label} ---")
        for item in option.items:
            lines.append(
                f"  {item.category} | {item.detail} | ${item.usd:g} | {item.inr:g} INR"
            )
        lines.append(f"  TOTAL ${option.total_usd:g} | {option.total_inr:g} INR")
    lines.append("")
    lines.append("2-day touring (cheap & free):")
    for stop in spec.touring_plan:
        lines.append(f"  {stop.time}: {stop.place} - {stop.note}")
    lines.append("")
    lines.append("Cheap dinner near hotel:")
    for dining in spec.dining_near_hotel:
        lines.append(f"  {dining.name} ({dining.cuisine}, {dining.price}, {dining.distance})")
    return "\n".join(lines) + "\n"


def evaluate_ultimate(decision: str, spec: UltimateChallengeSpec) -> dict:
    if not decision:
        return {
            "passed": False,
            "options": {option.label: {"found": False} for option in spec.options},
            "has_matrix": False,
            "has_touring_stops": False,
        }
    normalized = decision.replace(",", "").replace(" ", "").replace("\u00a0", "")
    per_option = {}
    for option in spec.options:
        usd_in_decision = f"{option.total_usd:g}" in normalized
        inr_in_decision = f"{option.total_inr:g}" in normalized
        per_option[option.label] = {
            "usd_in_decision": usd_in_decision,
            "inr_in_decision": inr_in_decision,
            "found": usd_in_decision and inr_in_decision,
        }
    all_options_found = all(entry["found"] for entry in per_option.values())
    has_matrix = "matrix" in decision.lower()
    has_touring = spec.touring_plan[0].place in decision
    return {
        "passed": all_options_found and has_matrix and has_touring,
        "options": per_option,
        "has_matrix": has_matrix,
        "has_touring_stops": has_touring,
    }


def build_ultimate_factory(
    spec: UltimateChallengeSpec,
    *,
    trace=None,
) -> Callable[[AgentDefinition], Callable[[str], AgentResult]]:
    """Factory seam for the ultimate challenge pool.

    Deterministic offline (golden reference). Set SOLVER_ADAPTER=llm to route
    research/planner through LlmAgent against a real model.
    """
    adapter = os.environ.get("SOLVER_ADAPTER", "deterministic")
    config = None
    if adapter == "llm":
        config = LlmConfig(
            base_url=os.environ.get("LLM_BASE_URL", "http://127.0.0.1:11434/v1"),
            model=os.environ.get("LLM_MODEL", "qwen3:8b"),
            api_key=os.environ.get("LLM_API_KEY", ""),
        )

    def factory(definition: AgentDefinition) -> Callable[[str], AgentResult]:
        if adapter == "llm":
            if definition.id == "trip_planner":
                payload = json.dumps(spec_payload(spec), indent=1)
                return lambda task: AgentResult(
                    agent_id=definition.id,
                    status="completed",
                    recommendation=chat(
                        replace(config, max_tokens=3000, reasoning_effort="low"),
                        ULTIMATE_SYSTEM,
                        payload,
                    ),
                    evidence=(f"llm:{config.model}",),
                    metadata={"thinking": definition.id},
                )
            agent = LlmAgent(definition, config)
            tools = granted_tools(definition)
            if tools:

                def live(task: str) -> AgentResult:
                    research = tools["websearch"](query=task)
                    note = research.get("note") or f"{len(research.get('items', []))} live results"
                    return AgentResult(
                        agent_id=definition.id,
                        status="completed",
                        recommendation=f"research note: {note}; full proposal assembled by trip_planner.",
                        evidence=("websearch", "offline-safe"),
                        metadata={"research": research},
                    )

                return live
            return agent.execute

        def deterministic(task: str) -> AgentResult:
            return AgentResult(
                agent_id=definition.id,
                status="completed",
                recommendation=golden_decision(spec),
                evidence=("golden-reference",),
            )

        return deterministic

    return factory