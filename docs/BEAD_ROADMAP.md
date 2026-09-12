# BEAD Roadmap — Dynamic ADK Agents

Ten beads take the project from a deterministic local pool to a registry-controlled,
model-backed agent pool that can solve the live-data **Ultimate Challenge**
(`docs/ultimate_challenge.md`) with web tools.

| BEAD | Title | Outcome | Status |
| --- | --- | --- | --- |
| 0 | Config & determinism contract | YAML config, typed `AgentDefinition`, bounded procedural determinism contract | done |
| 1 | Registry control plane + H2 + HITL engine | FastAPI/H2 registry (agents + MCP), policy fields, LangGraph reconciliation engine with pause/resume | done |
| 2 | Registry Client | ADK app fetches agents/MCP from the registry (never hard-coded); policy/contract/**approval** flags flow into execution context; fail-closed if registry down | in progress |
| 3 | Dynamic pool ops | enable/disable/version-rollback applied at runtime from the registry without redeploy | pending |
| 4 | Runtime policy enforcement | `AgentLimits` (timeout, max tool calls, iterations) + tool-allowlist violations audited in orchestrator | pending |
| 5 | Human-approval event surface | SSE/webhook for `requires_human_approval`; pause/resume contract exercised end-to-end | pending |
| 6 | Real ADK adapter | `LlmAgent`/`AgentTool` behind the factory seam, env-guarded, optional e2e test | pending |
| 7 | Tool/MCP boundary | Registry-granted external tools: `websearch`/`webfetch` as the first (for the Ultimate Challenge) | pending |
| 8 | Reconciliation metrics + regression suite | escalation/conflict rates, decision-trace export, replay of 10 benchmark problems via ADK evaluator | pending |
| 9 | Ultimate Challenge solve | Pool solves the NY trip plan live (web tools + model), produces matrix + 2 options meeting the pass criteria | pending |

## Principles enforced on every bead

- Offline-deterministic by default; models opt-in (`.env` guarded).
- No hard-coded MCP servers or agents in the ADK app — always via the registry client.
- Tests never consume Gemini quota; BDD features where behavior is user-visible.
- Commit after each bead; a bead counts done only when its tests pass.