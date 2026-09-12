from __future__ import annotations

from typing import Callable

from app.models import AgentDefinition, AgentResult
from app.solver.llm import LlmConfig, chat, llm_config_from_env

DEFAULT_AGENT_SYSTEM = (
    "You are a routing/optimization specialist agent on a deterministic team. "
    "Given only the problem data and your task, reason and then give your final answer in one "
    "short final paragraph. Format a route as A->B->C->A and state the total cost as a plain number. "
    "If no valid solution exists, state 'impossible' clearly."
)


class LlmAgent:
    """A real model-backed ADK adapter behind the factory seam.

    Env-guarded: the caller must provide ``config`` explicitly or have LLM_* env vars set
    (``.env`` is never read implicitly); deterministic offline by default.
    """

    def __init__(
        self,
        definition: AgentDefinition,
        config: LlmConfig | None = None,
        *,
        chat_fn: Callable[[LlmConfig, str, str], str] = chat,
        system: str = DEFAULT_AGENT_SYSTEM,
    ) -> None:
        self.definition = definition
        self.config = config or llm_config_from_env()
        self._chat = chat_fn
        self._system = system

    def execute(self, task: str) -> AgentResult:
        if not task or not task.strip():
            raise ValueError("agent task must not be empty")
        text = self._chat(self.config, self._system, task)
        return AgentResult(
            agent_id=self.definition.id,
            status="completed",
            recommendation=text,
            evidence=(f"llm:{self.config.model}",),
            metadata={"thinking": text, "model": self.config.model},
        )


class AgentTool:
    """Expose any resolved agent (deterministic or LlmAgent) as a callable tool.

    Mirrors ``app.agents.factory.AgentAsTool`` with an explicit ``execute`` callable
    and stable result contract; this is the ADK Agent-as-a-Tool shape (BEAD 6).
    """

    def __init__(self, agent_id: str, execute: Callable[[str], AgentResult]) -> None:
        self.name = f"{agent_id}_tool"
        self.agent_id = agent_id
        self._execute = execute

    def __call__(self, task: str) -> AgentResult:
        if not task or not task.strip():
            raise ValueError("agent tool task must not be empty")
        return self._execute(task)


def as_agent_tool(agent: LlmAgent) -> AgentTool:
    return AgentTool(agent.definition.id, agent.execute)