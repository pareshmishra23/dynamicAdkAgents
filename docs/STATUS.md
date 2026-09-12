# Status — Dynamic ADK Agents

> Generated: 2026-09-12 · branch `main` · last commit `4d661e6` (pushed to `origin/main`)

## 1. Test status

| Suite | Command | Result | Time |
| --- | --- | --- | --- |
| Root (ADK app + tools) | `.venv/bin/python -m pytest` | **110 passed, 1 skipped** | ~10 s |
| Registry service (FastAPI/H2) | `registry-service/.venv/bin/python -m pytest` | **61 passed, 3 warnings** | ~1 s |

Skipped test: the optional live-model e2e case (never consumes model quota by default).

### Unit-test inventory (`tests/unit/`)

| File | Coverage focus |
| --- | --- |
| `test_solver.py` | deterministic solver, all 10 benchmark problems, planner kinds |
| `test_ultimate_challenge.py` | golden NY-trip reference (USD exact, INR ±100 tolerance) |
| `test_registry.py`, `test_registry_client.py` | registry gates + client mapping, fail-closed when registry down |
| `test_langgraph_engine.py`, `test_orchestration.py`, `test_routing.py`, `test_adk_adapter.py` | reconciliation engine, orchestrator, resolver/contract, ADK adapter |
| `test_beads_3_to_5.py` | dynamic pool ops, policy enforcement, approval/event surface |
| `test_bead6_adapter.py` | `LlmAgent`/`AgentTool` + env-guarded factory seam |
| `test_bead7_web_tools.py` | `websearch`/`webfetch` boundary (offline-safe + localhost stub) |
| `test_bead8_metrics.py` | metrics collector, gold-versus-current comparator, escalation path |
| `test_bead9_ultimate.py` | ultimate-challenge evaluator + pool solve pass criteria |

## 2. Implementation status — BEAD roadmap

| BEAD | Title | Status | Evidence |
| --- | --- | --- | --- |
| 0 | Config & determinism contract | **done** | YAML config, typed `AgentDefinition`, bounded procedural determinism |
| 1 | Registry control plane + H2 + HITL | **done** | FastAPI/H2 registry (agents + MCP), policy fields, LangGraph pause/resume |
| 2 | Registry client | **done** | `RegistryClient` (fetch/enable/disable/update), approval flags flow into context |
| 3 | Dynamic pool ops | **done** | `DynamicPool` refresh/add/disable/rollback without redeploy |
| 4 | Runtime policy enforcement | **done** | allowlist + timeout + `max_tool_calls`, run ends `policy_violation` (audited) |
| 5 | Human-approval event surface | **done** | `ApprovalEventBus`/SSE/webhook, approve/reject → completed/rejected |
| 6 | Real ADK adapter | **done** | `LlmAgent`/`AgentTool` behind `build_solver_factory`, env-guarded (`SOLVER_ADAPTER=llm`) |
| 7 | Tool/MCP boundary | **done** | functional `websearch`/`webfetch`, grant-only for `research_agent`, offline-safe |
| 8 | Reconciliation metrics + regression | **done** | `app/metrics.py`, golden in `golden/metrics.json`, replay 10/10, 0 regressions |
| 9 | Ultimate Challenge solve | **done** | NY pool solves spec; offline + live model solve both `passed=True` |

**All 10 beads complete.**

## 3. Benchmark / experiment status

| Benchmark | Result | Details |
| --- | --- | --- |
| Deterministic solver (P1–P10) | **10/10 PASS** | 8 EXCELLENT, 2 GOOD (`docs/benchmark_report.md`) |
| Regression replay | **10/10, 0 regressions** | deterministic replay vs golden (`docs/BENCHMARK_REGRESSION.md`) |
| LLM experiment (gpt-oss-20b) | see next section | `docs/LLM_SOLVER_EXPERIMENT.md` |
| Ultimate Challenge (offline) | **passed=True** | golden reference path, ~4 ms |
| Ultimate Challenge (live model) | **passed=True** | NVIDIA `openai/gpt-oss-20b`, `reasoning_effort=low`, ~24 s |

### LLM experiment (raw model, no grounding)

- Problems 1–6: **exact optima** (45/40/60/25/60/110) · P9/P10 correct abstains · **10/10 string-PASS**
- P7 (15-city) and P8 (VRP) not groundable from raw model output
- Determinism: **not bit-for-bit at temperature 0** (hosted endpoint) → tool-grounded solver stays the decision layer

## 4. Runtime posture

- Offline-deterministic by default; model access is opt-in via gitignored `.env`
  (`LLM_BASE_URL` / `LLM_MODEL` / `LLM_API_KEY`, currently NVIDIA gpt-oss-20b). No secrets in the repo.
- Policy + execution contract documented in `docs/RUNTIME_POLICY.md` (enforcement ✅ for beads 1–7).

## 5. Remaining / known gaps

- P7/P8 (15-city and VRP) are not solvable by the raw model alone — they need the
  tool-grounded route/plan layer (already how the deterministic solver works).
- No CI pipeline yet (test commands above stand in).
- `Archive.zip` and `TSP-50-Agent-Benchmark.md` remain untracked (kept out of the repo deliberately).