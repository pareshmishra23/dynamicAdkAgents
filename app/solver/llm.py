from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

from app.models import AgentDefinition, AgentResult
from app.solver.problems import RoutingProblem


class LlmCallError(RuntimeError):
    pass


@dataclass(frozen=True)
class LlmConfig:
    base_url: str = "http://127.0.0.1:11434/v1"
    model: str = "qwen3:8b"
    api_key: str = ""
    temperature: float = 0.0
    max_tokens: int = 512
    timeout_seconds: float = 120.0
    reasoning_effort: str | None = None


def llm_config_from_env(overrides: dict[str, str] | None = None) -> LlmConfig:
    env = os.environ
    values = {
        "LLM_BASE_URL": env.get("LLM_BASE_URL", "http://127.0.0.1:11434/v1"),
        "LLM_MODEL": env.get("LLM_MODEL", "qwen3:8b"),
        "LLM_API_KEY": env.get("LLM_API_KEY", ""),
    }
    if overrides:
        values.update({key: value for key, value in overrides.items() if value is not None})
    return LlmConfig(
        base_url=values["LLM_BASE_URL"].rstrip("/"),
        model=values["LLM_MODEL"],
        api_key=values.get("LLM_API_KEY", ""),
    )


def problem_payload(problem: RoutingProblem) -> dict[str, Any]:
    return {
        "id": problem.id,
        "title": problem.title,
        "cities": list(problem.cities),
        "edges": [{"a": e.a, "b": e.b, "cost": e.cost} for e in problem.edges],
        "directed": problem.directed,
        "kind": problem.kind,
        "impossible": problem.impossible,
        "precedence": [list(pair) for pair in problem.precedence],
        "first_stop_after_start": problem.first_stop_after_start,
        "notes": problem.notes,
    }


def chat(config: LlmConfig, system: str, user: str) -> str:
    url = config.base_url + "/chat/completions"
    body = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
        "stream": False,
    }
    if config.reasoning_effort:
        body["reasoning_effort"] = config.reasoning_effort
    headers = {"Content-Type": "application/json"}
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=config.timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, OSError, ValueError, TimeoutError) as exc:
        raise LlmCallError(f"llm call to {url} failed: {exc}") from exc
    choices = payload.get("choices") or []
    if not choices:
        raise LlmCallError(f"llm returned no choices: {payload.get('error') or payload}")
    content = str(choices[0].get("message", {}).get("content", "")).strip()
    if not content:
        raise LlmCallError("llm returned an empty message")
    return content


def make_llm_solver_factory(
    problem: RoutingProblem,
    config: LlmConfig | None = None,
    trace=None,
) -> Callable[[AgentDefinition], Callable[[str], AgentResult]]:
    config = config or llm_config_from_env()

    def factory(definition: AgentDefinition) -> Callable[[str], AgentResult]:
        ctx = trace.named(definition.id) if trace else None

        def execute(task: str) -> AgentResult:
            system = (
                "You are a routing/optimization specialist agent on a deterministic team. "
                "Given only the problem data and your task, reason and then give your final answer in one "
                "short final paragraph. Format a route as A->B->C->A and state the total cost as a plain number. "
                "If no valid solution exists, state 'impossible' clearly."
            )
            user = (
                "PROBLEM DATA:\n"
                + json.dumps(problem_payload(problem), indent=1)
                + f"\n\nYOUR TASK: {task}\n\nGive your final answer."
            )
            if ctx:
                ctx.pointer(f"asking {config.model} (temperature={config.temperature}) for {definition.id}")
            text = chat(config, system, user)
            if ctx:
                ctx.act(f"{definition.id} model reply: {text[:200]}")
            return AgentResult(
                agent_id=definition.id,
                status="completed",
                recommendation=text,
                evidence=(f"llm:{config.model}",),
                metadata={"thinking": text},
            )

        return execute

    return factory