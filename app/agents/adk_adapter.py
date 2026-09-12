from __future__ import annotations

from typing import Any, Iterable

from app.models import AgentDefinition


class ADKUnavailableError(RuntimeError):
    """Raised when the optional Google ADK dependency is not installed."""


def build_adk_agent(
    definition: AgentDefinition,
    *,
    model: str,
    tools: Iterable[Any] = (),
):
    """Build one Google ADK LlmAgent on demand.

    The import is intentionally lazy so unit tests and the deterministic local
    demo do not require Gemini credentials or the ADK package.
    """
    try:
        from google.adk.agents import LlmAgent
    except ImportError as exc:
        raise ADKUnavailableError(
            "Google ADK is not installed; install the optional 'adk' extra to enable the real adapter"
        ) from exc

    return LlmAgent(
        name=definition.id,
        model=model,
        description=definition.description,
        instruction=definition.instructions,
        tools=list(tools),
    )


def build_agent_tool(agent: Any):
    """Wrap an ADK agent using the official AgentTool adapter."""
    try:
        from google.adk.tools import AgentTool
    except ImportError as exc:
        raise ADKUnavailableError(
            "Google ADK is not installed; install the optional 'adk' extra to enable AgentTool"
        ) from exc
    return AgentTool(agent=agent)
