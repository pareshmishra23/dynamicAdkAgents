from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable

from app.models import AgentDefinition, AgentResult, ToolSpec


class PolicyViolation(RuntimeError):
    pass


@dataclass
class PolicyAudit:
    entries: list[str] = field(default_factory=list)

    def record(self, message: str) -> None:
        self.entries.append(message)


class ToolRegistry:
    def __init__(self, specs: tuple[ToolSpec, ...] = ()) -> None:
        self._specs = {spec.name: spec for spec in specs}

    def register(self, spec: ToolSpec) -> None:
        self._specs[spec.name] = spec

    def known(self, tool_name: str) -> bool:
        return tool_name in self._specs

    def allowed_for(self, tool_name: str, agent_id: str) -> bool:
        spec = self._specs.get(tool_name)
        if spec is None:
            return False
        return not spec.allowed_agent_ids or agent_id in spec.allowed_agent_ids

    def names(self) -> tuple[str, ...]:
        return tuple(self._specs)


class PolicyEnforcer:
    def __init__(self, tools: ToolRegistry, audit: PolicyAudit | None = None) -> None:
        self.tools = tools
        self.audit = audit or PolicyAudit()

    def _violation(self, agent_id: str, message: str) -> AgentResult:
        self.audit.record(message)
        return AgentResult(
            agent_id=agent_id,
            status="policy_violation",
            recommendation=message,
            evidence=(message,),
        )

    def wrap(
        self,
        definition: AgentDefinition,
        execute: Callable[[str], AgentResult],
    ) -> Callable[[str], AgentResult]:
        def guarded(task: str) -> AgentResult:
            disallowed = [
                name
                for name in definition.allowed_tools
                if not self.tools.known(name) or not self.tools.allowed_for(name, definition.id)
            ]
            if disallowed:
                return self._violation(
                    definition.id,
                    f"tool allowlist violation for {definition.id}: "
                    + ", ".join(disallowed)
                    + " not granted (audit logged)",
                )
            started = self._now()

            def timed() -> AgentResult:
                result = execute(task)
                tool_calls = int(result.metadata.get("tool_calls", len(definition.allowed_tools) or 1))
                if tool_calls > definition.limits.max_tool_calls:
                    return self._violation(
                        definition.id,
                        f"max_tool_calls exceeded for {definition.id}: {tool_calls} > "
                        f"{definition.limits.max_tool_calls} (audit logged)",
                    )
                return result

            timeout = definition.limits.timeout_seconds
            try:
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(timed)
                    result = future.result(timeout=timeout)
            except TimeoutError:
                return self._violation(
                    definition.id,
                    f"timeout({timeout}s) exceeded for {definition.id}: {self._elapsed_ms(started)}ms "
                    "(audit logged)",
                )
            self.audit.record(f"{definition.id} ok: allowlist={list(definition.allowed_tools)} limit={timeout}s")
            return result

        return guarded

    def _now(self) -> float:
        import time

        return time.perf_counter()

    def _elapsed_ms(self, started: float) -> int:
        import time

        return int((time.perf_counter() - started) * 1000)