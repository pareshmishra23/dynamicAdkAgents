# BEAD Roadmap — Dynamic ADK Agents

Ten beads take the project from a deterministic local pool to a registry-controlled,
model-backed agent pool that can solve the live-data **Ultimate Challenge**
(`docs/ultimate_challenge.md`) with web tools.

| BEAD | Title | Outcome | Status |
| --- | --- | --- | --- |
| 0 | Config & determinism contract | YAML config, typed `AgentDefinition`, bounded procedural determinism contract | done |
| 1 | Registry control plane + H2 + HITL engine | FastAPI/H2 registry (agents + MCP), policy fields, LangGraph reconciliation engine with pause/resume | done |
| 2 | Registry Client | ADK app fetches agents/MCP from the registry (never hard-coded); policy/contract/**approval** flags flow into execution context; fail-closed if registry down | done |
| 3 | Dynamic pool ops | enable/disable/version-rollback applied at runtime from the registry without redeploy | done |
| 4 | Runtime policy enforcement | `AgentLimits` (timeout, max tool calls, iterations) + tool-allowlist violations audited in orchestrator | done |
| 5 | Human-approval event surface | SSE/webhook for `requires_human_approval`; pause/resume contract exercised end-to-end | done |
| 6 | Real ADK adapter | `LlmAgent`/`AgentTool` behind the factory seam, env-guarded, optional e2e test | done |
| 7 | Tool/MCP boundary | Registry-granted external tools: `websearch`/`webfetch` as the first (for the Ultimate Challenge) | done |
| 8 | Reconciliation metrics + regression suite | escalation/conflict rates, decision-trace export, replay of 10 benchmark problems via ADK evaluator | done |
| 9 | Ultimate Challenge solve | Pool solves the NY trip plan live (web tools + model), produces matrix + 2 options meeting the pass criteria | done |

## Principles enforced on every bead

- Offline-deterministic by default; models opt-in (`.env` guarded).
- No hard-coded MCP servers or agents in the ADK app — always via the registry client.
- Tests never consume Gemini quota; BDD features where behavior is user-visible.
- Commit after each bead; a bead counts done only when its tests pass.

## Beads 6-9 notes

- **BEAD 6** — `app/agents/adapter.py` (`LlmAgent`, `AgentTool`), solver default via
  `app/solver/factory.build_solver_factory`: deterministic unless `SOLVER_ADAPTER=llm`.
  LlmAgent is OpenAI-compatible (`/v1/chat/completions`), so it works with Ollama or any
  hosted endpoint from `.env` (`LLM_BASE_URL`/`LLM_MODEL`/`LLM_API_KEY`).
- **BEAD 7** — `app/tools/web.py` supplies functional `websearch`/`webfetch`
  (`granted_tools`, offline-safe: without `WEBSEARCH_PROVIDER=http`+`WEBSEARCH_ENDPOINT` they
  return an explicit `unavailable` note, never invented data). `research_agent` holds the grant.
- **BEAD 8** — `app/metrics.py` ($status/`passed`/`iterations`/`tool_calls`/`escalation`,
  JSON export, golden comparator); `scripts/run_regression.py` replays the 10 problems,
  exports decision traces to `logs/regression/`, and compares to `golden/metrics.json`.
- **BEAD 9** — `app/solver/ultimate_solver.py` + `scripts/solve_ultimate_challenge.py` run
  the NY pool; `evaluate_ultimate` enforces pass criteria (both option totals - USD and INR -
  present, cost matrix, Times Square touring stop). Live solve against a real model:
  `SOLVER_ADAPTER=llm` → `docs/ULTIMATE_CHALLENGE_SOLVE.md` (passed=True).
- **Benchmarks landed**: `docs/LLM_SOLVER_EXPERIMENT.md` (raw gpt-oss-20b: exact optima on
  6/8 solvable, 10/10 string PASS, non-deterministic at temp 0) and
  `docs/BENCHMARK_REGRESSION.md` (deterministic replay 10/10, 0 regressions).