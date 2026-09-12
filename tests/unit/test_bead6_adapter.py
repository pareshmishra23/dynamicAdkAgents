import os

import pytest

from app.agents.adapter import AgentTool, LlmAgent, as_agent_tool
from app.models import AgentDefinition, AgentResult
from app.solver.factory import build_solver_factory
from app.solver.llm import LlmConfig, llm_config_from_env
from app.solver.problems import BENCHMARK_PROBLEMS
from app.solver.planner import plan_agents
from app.solver.runner import solve_problem


def make_def(agent_id: str = "llm_agent", model: str = "openai/gpt-oss-20b") -> AgentDefinition:
    return AgentDefinition(
        id=agent_id,
        version="v1",
        enabled=True,
        name=f"{agent_id} name",
        description="model-backed agent",
        capabilities=("advise",),
        instructions="advise",
        input_contract={},
        output_contract={"type": "object", "properties": {}},
        model=model,
    )


class TestLlmConfigFromEnv:
    def test_defaults_are_local_ollama(self):
        cfg = llm_config_from_env(overrides={})
        assert cfg.base_url == "http://127.0.0.1:11434/v1"
        assert cfg.model == "qwen3:8b"
        assert cfg.temperature == 0.0

    def test_overrides_win(self):
        cfg = llm_config_from_env(
            overrides={
                "LLM_BASE_URL": "https://integrate.api.nvidia.com/v1",
                "LLM_MODEL": "openai/gpt-oss-20b",
                "LLM_API_KEY": "nvapi-test",
            }
        )
        assert cfg.base_url == "https://integrate.api.nvidia.com/v1"
        assert cfg.model == "openai/gpt-oss-20b"
        assert cfg.api_key == "nvapi-test"

    def test_trailing_slash_stripped(self):
        cfg = llm_config_from_env(overrides={"LLM_BASE_URL": "http://x/v1/"})
        assert cfg.base_url == "http://x/v1"


class TestLlmAgent:
    def test_execute_returns_contract_result(self):
        def fake_chat(config, system, user):
            assert config.model == "openai/gpt-oss-20b"
            return "A->B->C->A cost 45"

        agent = LlmAgent(make_def(), LlmConfig(model="openai/gpt-oss-20b"), chat_fn=fake_chat)
        result = agent.execute("solve this")
        assert isinstance(result, AgentResult)
        assert result.status == "completed"
        assert "A->B->C->A" in result.recommendation
        assert result.evidence == ("llm:openai/gpt-oss-20b",)

    def test_execute_empty_task_rejected(self):
        agent = LlmAgent(make_def(), LlmConfig(), chat_fn=lambda *a: "x")
        with pytest.raises(ValueError):
            agent.execute("   ")

    def test_explicit_config_beats_env(self, monkeypatch):
        monkeypatch.setenv("LLM_MODEL", "llama-from-env")
        agent = LlmAgent(make_def(), LlmConfig(model="pinned-model"), chat_fn=lambda *a: "x")
        assert agent.config.model == "pinned-model"


class TestAgentTool:
    def test_wraps_execute_and_flatmaps_contract(self):
        tool = AgentTool("llm_agent", lambda task: AgentResult("llm_agent", "completed", task))
        assert tool.name == "llm_agent_tool"
        assert tool.agent_id == "llm_agent"
        assert tool("do it").recommendation == "do it"

    def test_empty_task_rejected(self):
        tool = AgentTool("a", lambda task: AgentResult("a", "completed", task))
        with pytest.raises(ValueError):
            tool("")

    def test_as_agent_tool(self):
        agent = LlmAgent(make_def(), LlmConfig(), chat_fn=lambda *a: "done")
        tool = as_agent_tool(agent)
        assert tool.agent_id == "llm_agent"


class TestSolverFactorySeam:
    def test_default_adapter_is_deterministic(self, monkeypatch):
        monkeypatch.delenv("SOLVER_ADAPTER", raising=False)
        problem0 = BENCHMARK_PROBLEMS[0]
        planned = plan_agents(problem0).agents[0]
        factory = build_solver_factory(problem0)
        result = factory(planned.definition)("delegate")
        assert result.status == "completed"

    def test_llm_adapter_env_gate(self, monkeypatch):
        monkeypatch.setenv("SOLVER_ADAPTER", "llm")
        monkeypatch.setenv("LLM_BASE_URL", "http://test/v1")
        monkeypatch.setenv("LLM_MODEL", "tt")
        monkeypatch.setattr(
            "app.solver.llm.chat",
            lambda config, system, user: "A->B->C->D->E->A with total cost 45",
        )
        problem0 = BENCHMARK_PROBLEMS[0]
        run = solve_problem(problem0)
        assert run.result.status == "completed"

    def test_random_env_value_is_safe(self, monkeypatch):
        monkeypatch.setenv("SOLVER_ADAPTER", "bogus")
        factory = build_solver_factory(BENCHMARK_PROBLEMS[0])
        assert factory is not None


class TestExperimentOptInNoNetwork:
    def test_solve_problem_without_env_is_deterministic(self, monkeypatch):
        for var in ("SOLVER_ADAPTER", "LLM_BASE_URL", "LLM_MODEL", "LLM_API_KEY"):
            monkeypatch.delenv(var, raising=False)
        run = solve_problem(BENCHMARK_PROBLEMS[0])
        assert run.passed() is True
        assert run.result.status == "completed"