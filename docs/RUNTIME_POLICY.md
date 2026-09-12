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

## 4. Deployment posture

- **Realtime / interactive:** `temperature=0`, pinned `seed`, enabled-only registry
  lookups, bounded loops. This is the default and is fully local.
- **Creative / batch (opt-in only):** raise `temperature` per agent via `policy`.
  The contract above still applies to routing, tools, and decision path.

## 5. Determinism tests (no Gemini needed)

- **Golden runs:** frozen registry snapshot + frozen model version → assert same agent
  selection and same ordered tool-call sequence across runs.
- **Mutation tests:** prove the system rejects invented agent IDs, disabled agents, and
  unknown capabilities (registry 404/409 semantics — already covered by unit + BDD).
- **Replay:** same input executed twice → identical tool sequences and result contract
  conformance.

## 6. Current enforcement status

| Bead | Enforced? |
| --- | --- |
| BEAD 1 — registry gates (exists/enabled/duplicate) + `policy` field with deterministic defaults | ✅ today |
| BEAD 2 — Registry Client passes `policy` to the ADK execution context | next |
| BEAD 3 — enabled-only MCP discovery, no disabled exposure | next |
| BEAD 4 — capability → tool resolution, provider allowlist | next |
| BEAD 5 — router constrained selection + authorization gate | next |
| BEAD 6 — only selected+authorized agents become Agent-as-a-Tool | next |
| BEAD 7 — orchestrator enforces timeouts, `max_iterations`, audit envelope | next |