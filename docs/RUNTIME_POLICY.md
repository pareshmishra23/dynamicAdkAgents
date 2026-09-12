# Runtime Policy — Determinism Contract

> Status: v0.1 — governing document for the dynamic ADK agent pool
> (registry `registry-service/` + ADK app + orchestrator).

LLM output is probabilistic by nature. **This project does not promise identical prose.**
It promises *bounded, procedural determinism*: given the same input, registry state, and
pinned model version, the system always selects the same agents, calls the same tools,
follows the same decision path, and returns a contract-valid result.

## 1. What "deterministic" means here

| Level | Guaranteed? | Policy |
| --- | --- | --- |
| Agent selection | Yes | Router emits registry IDs only; validated against registry (exists → enabled) |
| Tool binding | Yes | Agent requests a *capability*; registry maps capability → MCP server → tools |
| Tool set per run | Yes | Enabled-only; disabled/unknown rejected (404 / 409 / empty result), never guessed |
| Decision path | Yes | Orchestrator owns the final decision; specialists only produce evidence |
| Loop termination | Yes | Critic/refiner bounded by `max_iterations`; per-agent timeouts |
| Output validity | Yes | Output must match the agent's contract (schema); fail-fast on violation |
| Byte-identical prose | No | Impossible for a sampling model; not a goal |

## 2. Per-agent policy contract

Lives in the registry on the `agents` table (`policy` JSON column). Defaults are
*already deterministic* so a misconfigured agent fails closed, not open.

| Field | Default | Meaning |
| --- | --- | --- |
| `temperature` | `0.0` | Sampling temperature; 0.0 = greedy decoding |
| `seed` | `null` | Fixed RNG seed for reproducible runs (pin per deployment) |
| `timeout_seconds` | `60` | Hard wall-clock budget per agent invocation |
| `max_tool_calls` | `20` | Upper bound on tool calls per invocation |
| `max_retries` | `2` | Retries before the planner-critical path fails |
| `max_iterations` | `3` | Critic/refiner loop bound (orchestrator) |

Validation rules (enforced by the registry API, 4xx on violation):
- `temperature` in `[0.0, 2.0]`
- `timeout_seconds`, `max_tool_calls`, `max_iterations` strictly positive
- `max_retries` non-negative
- Unknown agent IDs rejected at registration time when referenced from tools

## 3. Execution rules

1. **Pin the model.** `agents.model` is the exact model identifier. Upgrading a model
   is an explicit registry change, never silent drift.
2. **Constrained router output.** The router must return a JSON object
   `{"agents": [id, ...]}`; single retry on parse/schema failure, reject on the second.
3. **No free-form tool selection.** The LLM never supplies endpoints, URLs, or tool
   names — it supplies capabilities; the registry resolves them.
4. **Retry once, then fail.** Failures follow `max_retries`, then the run fails (or
   abstains: `abstain_human_review`) instead of degrading silently.
5. **Validate before propagate.** Every specialist result is checked against its
   contract; violations do not reach the orchestrator.
6. **Audit every decision.** Each run records: selected agents, rejected IDs, disabled
   lookups, blocked tools, retries, and final status (the PDF result envelope:
   `run_id`, `agent_id`, `status`, `output`, `tool_calls`, `duration_ms`).

## 4. Conflict & Reconciliation Protocol

Agents are *small tasks*; conflicts still happen when their decisive outputs collide
(two specialists claim the same user need, or carry contradictory evidence). The pool
resolves them the way a code agent resolves a merge conflict — never by hope.

| Code agent (merge) | Agent pool |
| --- | --- |
| Edit overlap conflict | Conflicting specialist recommendations / mutually exclusive evidence |
| Conflict detection | **Critic** — structured check on the proposal (overlap, contradiction, contract) |
| Deterministic resolution | **Reconciliation rules** — capability precedence / orchestrator tie-break, *not* LLM debate |
| Rebase / merge | **Refiner** — applies the resolved direction |
| Conflict markers → human | `abstain_human_review` — the run stops decisively |
| Never silent corruption | Invalid or contradictory output never propagates |

Rules:

1. **Detect as data.** A conflict is a structured event (`issue`), not a vibe.
2. **Resolve by rule first.** Precedence table wins; the LLM only refines *within* the
   resolved direction.
3. **Bounded looping.** Critic/refiner runs at most `max_iterations` (default 3).
4. **Decisive stop.** On exhaustion the run ends `abstain_human_review` — it declares
   the conflict rather than guessing.

## 5. Human-in-the-Loop (HITL) policy

Some agents are policy-marked `requires_human_approval: true` (registry field). These
must not execute on an automated decision alone.

- **Gate before execution.** Selected agents flagged for approval pause the run and
  emit `awaiting_human_approval` with the pending agent id.
- **Explicit resolution.** A human approves or rejects per agent; rejected agents are
  excluded from the run, approved agents proceed. The decision is recorded.
- **No partial silence.** If every selected agent is rejected → `no_agents_authorized`.
- **Escalation outcomes.** Unresolved critic loops end in `abstain_human_review`; both
  escalation states are first-class results, not errors.
- **Audit.** Approver action, timestamp, agent id, and final status are recorded.

Implementation: the LangGraph engine uses a native checkpointed `interrupt()` gate, so
approval survives process restarts via the checkpointer.

## 6. Orchestration engines

Two engines, one contract. Pick by case, not by preference.

| Engine | Use for | Properties |
| --- | --- | --- |
| `app.agents.orchestrator` (default) | Plain parallel / sequential runs | Zero extra deps, deterministic, fast |
| `app.agents.langgraph_engine.LangGraphOrchestrator` (optional `[graph]`) | HITL approval, conflict reconciliation, error-recovery, pause/resume | Stateful checkpointed graph, native `interrupt()`/resume, bounded critic loop |

Both honour `max_iterations`, `max_parallel_agents`, and the same result contract.

## 7. Deployment posture

- **Realtime / interactive:** `temperature=0`, pinned `seed`, enabled-only registry
  lookups, bounded loops. This is the default and is fully local.
- **Creative / batch (opt-in only):** raise `temperature` per agent via `policy`.
  The contract above still applies to routing, tools, and decision path.
- **Approval-required actions:** HITL gate is mandatory regardless of posture.

## 8. Determinism tests (no Gemini needed)

- **Golden runs:** frozen registry snapshot + frozen model version → assert same agent
  selection and same ordered tool-call sequence across runs.
- **Mutation tests:** prove the system rejects invented agent IDs, disabled agents, and
  unknown capabilities (registry 404/409 semantics — already covered by unit + BDD).
- **Replay:** same input executed twice → identical tool sequences and result contract
  conformance.
- **Reconciliation tests:** critic/refiner terminates within `max_iterations`; HITL
  pauses on approval-required agents and resumes to a decisive outcome.

## 9. Current enforcement status

| Bead | Enforced? |
| --- | --- |
| BEAD 1 — registry gates (exists/enabled/duplicate) + `policy` + `output_contract` + `requires_human_approval` | ✅ today |
| BEAD 2 — Registry Client passes `policy` / contract / approval flag to the ADK execution context | ✅ today |
| BEAD 3 — enabled-only MCP discovery, no disabled exposure | ✅ today |
| BEAD 4 — capability → tool resolution, provider allowlist | ✅ today (`PolicyEnforcer`: allowlist + timeout + `max_tool_calls`, run ends `policy_violation`) |
| BEAD 5 — router constrained selection + authorization gate | ✅ today (`ApprovalEventBus` / webhook / `EventStream`, pause/resume end-to-end) |
| BEAD 6 — only selected+authorized agents become Agent-as-a-Tool | ✅ today (`AgentTool`/`LlmAgent`, env-guarded; solver default stays deterministic) |
| BEAD 7 — orchestrator enforces timeouts, `max_iterations`, audit envelope, conflict protocol | ✅ today (LangGraph engine); `websearch`/`webfetch` functional + offline-safe for `research_agent` |

### Runtime pool ops (BEAD 3)

`app/registry/pool.DynamicPool` owns the in-memory registry and is driven by the
registry control plane at runtime, with no redeploy: `refresh()` applies add /
remove (disables, never deletes) / version-change diffs; `enable()` / `disable()` /
`rollback_version()` mutate local + remote state. Every op emits a notify and a
`PoolRefreshReport` (added/disabled/version_changed/total_enabled).

### Policy enforcement (BEAD 4)

`app/registry.policy.PolicyEnforcer` + `ToolRegistry` wrap every resolved agent
before execution: unknown or ungranted tool names and `max_tool_calls` breaches
fail with an audited `policy_violation`; `timeout_seconds` is a wall-clock cap.
Violations force the run to end with status `policy_violation` (fail-closed, never
a silent success). `websearch`/`webfetch` are registered, grant-only for `research_agent` (BEAD 7), and
**offline-safe**: without `WEBSEARCH_PROVIDER=http` + `WEBSEARCH_ENDPOINT` they return an
explicit `unavailable` note instead of inventing data.

### Approval events (BEAD 5)

`app/agents/events.ApprovalEventBus` emits `approval_pending`, `approval_approved`,
`approval_rejected` per agent per run. Sinks: in-process subscribers
(`EventStream` for SSE-style consumption) or `WebhookSink` (HTTP POST). The
LangGraph engine publishes these automatically when a
`requires_human_approval` agent crosses the gate; `resume(run_id, "approved"|"rejected")`
is the pause/resume contract, with the run ending `approved`/`rejected` recorded.