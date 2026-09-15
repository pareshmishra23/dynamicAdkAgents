from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable


class SecurityPolicyViolation(ValueError):
    """Raised when an LLM attempts to output forbidden direct infrastructure selectors."""
    pass


class InvalidCapabilityError(ValueError):
    """Raised when an unrecognized capability format is encountered."""
    pass


FORBIDDEN_PATTERNS = (
    re.compile(r"https?://", re.IGNORECASE),
    re.compile(r"stdio://", re.IGNORECASE),
    re.compile(r"jdbc:", re.IGNORECASE),
    re.compile(r"/api/v1/", re.IGNORECASE),
    re.compile(r"SELECT\s+.+\s+FROM", re.IGNORECASE),
    re.compile(r"localhost:\d+", re.IGNORECASE),
    re.compile(r"\b(rm|cat|bash|sh|exec|sudo)\b", re.IGNORECASE),
)

VALID_CAPABILITY_REGEX = re.compile(r"^[a-z0-9_]{3,64}$")


@dataclass(frozen=True)
class TaskIntent:
    capabilities: tuple[str, ...]
    task_summary: str
    metadata: dict[str, Any] = field(default_factory=dict)


class TaskAnalyzer:
    """Analyzes user requests into structured capability requirements.

    SECURITY RULE:
    The LLM cannot directly select URLs, databases, MCP endpoints, or arbitrary tools.
    It selects abstract capabilities. The registry resolves the actual implementation.
    """

    def __init__(self, llm_invoker: Callable[[str], dict[str, Any]] | None = None) -> None:
        self._llm_invoker = llm_invoker

    def sanitize_capabilities(self, raw_capabilities: list[str] | tuple[str, ...]) -> tuple[str, ...]:
        sanitized: list[str] = []
        for raw in raw_capabilities:
            text = str(raw).strip()
            # Security check against direct endpoint/URL injection
            for pattern in FORBIDDEN_PATTERNS:
                if pattern.search(text):
                    raise SecurityPolicyViolation(
                        f"Security violation: LLM proposed infrastructure/endpoint instead of capability: {text!r}"
                    )

            cleaned = text.lower().replace("-", "_")
            if not VALID_CAPABILITY_REGEX.match(cleaned):
                raise InvalidCapabilityError(f"Invalid capability format: {text!r}")
            sanitized.append(cleaned)
        return tuple(dict.fromkeys(sanitized))  # Deduplicate preserving order

    def analyze(self, user_query: str) -> TaskIntent:
        # If an external LLM invoker is configured, call it
        if self._llm_invoker is not None:
            raw_response = self._llm_invoker(user_query)
            caps = raw_response.get("capabilities", [])
            summary = raw_response.get("task_summary", user_query[:100])
            sanitized_caps = self.sanitize_capabilities(caps)
            return TaskIntent(capabilities=sanitized_caps, task_summary=summary)

        # Deterministic / offline capability extraction
        lowered = user_query.lower()
        capabilities: list[str] = []

        if any(term in lowered for term in ("vrp", "vehicle", "split", "fleet", "capacity")):
            capabilities.append("vrp_partitioning")
            capabilities.append("constraint_reasoning")

        if any(term in lowered for term in ("ordering", "precedence", "before", "after", "circular", "time-paradox", "constraint")):
            capabilities.append("constraint_reasoning")

        if any(term in lowered for term in ("island", "disconnected", "graph", "matrix", "distance", "edges")):
            capabilities.append("graph_analysis")

        if any(term in lowered for term in ("route", "routing", "tsp", "tour", "shortest", "cities", "travel", "highway", "one-way")):
            capabilities.append("route_optimization")

        if not capabilities:
            capabilities.append("route_optimization")

        sanitized_caps = self.sanitize_capabilities(capabilities)
        return TaskIntent(
            capabilities=sanitized_caps,
            task_summary=user_query.strip(),
        )
