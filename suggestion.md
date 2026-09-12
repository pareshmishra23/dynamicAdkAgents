# Suggestion — What to Actually Build (and What ADK Already Gives You)

> Good, that confirms it — that's just third-party documentation text in the search results (some unrelated Go package's internal jargon), not an instruction aimed at me, and it doesn't change what I'm doing here. Continuing with the research.

**Bottom line: yes, it's buildable — and you'd actually be building less than the doc suggests.**

Google ADK already ships native versions of most of sections 2, 6, 7, 8, and 9. The plan reinvents several primitives that already exist, so the real engineering effort is narrower than "15 sections" implies:

| Plan concept | ADK already gives you this | You still have to build |
| --- | --- | --- |
| Sequential/parallel/conditional planner | `SequentialAgent`, `ParallelAgent`, `LoopAgent` — deterministic, no LLM needed to orchestrate them | — |
| "Expose one agent as a tool to another" | `AgentTool` — wraps any agent as a callable tool automatically, no manual invoke/extract boilerplate | — |
| Runtime policy (timeouts, permissions, tool allowlists) | `before_tool_callback` / `after_tool_callback` / `before_model_callback` can block, validate, or mock a call before it runs | Your specific policy rules |
| Agent registry (YAML → running agent) | Recent ADK versions added declarative YAML-based Agent Config, so you don't have to hand-write the loader in section 4 | Hot-add/remove/version without redeploy — not native |
| State & observability | Session state + OpenTelemetry traces out of the box | Your own dashboards/alerts on top |
| Dynamic pool ops (enable_agent, remove_agent, rollback) | Not built-in | Yes — this is genuinely custom |
| Python program sandboxing | Not built-in | Yes — genuinely custom |
| Conflict arbitration + human escalation | Not built-in as a concept | Yes — see below |

**So narrow your actual scope to three things:** the dynamic registration/versioning layer, the Python sandbox, and the arbitration/escalation logic. Everything else is configuration on top of ADK, not code you write from scratch.

## Conflict and reconciliation, concretely

"Conflict" in a coding-agent pool is really four different problems, and they need different fixes — treating them the same way is the most common design mistake:

| Conflict type | Example | How it gets resolved |
| --- | --- | --- |
| Semantic disagreement | reviewer-agent rejects what coder-agent marked done | Critic/reviser loop (`LoopAgent`), capped at `max_iterations`; if it doesn't converge, escalate rather than loop forever |
| Non-deterministic answers | two parallel runs of the same question give different results | Join strategies: `majority_vote`, `first_success`, or a separate low-temperature "judge" agent that scores outputs against the `output_schema` — this is already in section 9 of your doc, it's the right tool |
| Write/resource conflict | two agents editing the same file or branch | Don't parallelize writers. Run analysis/review agents in parallel (read-only, like your code-quality-audit example), serialize the actual patch application through one writer per branch, one git worktree per agent |
| Policy/permission conflict | agent calls a tool outside its allowed list | Not resolved by consensus at all — hard stop via `before_tool_callback`, logged as a violation, run halted |

This is the same shape of problem your [[jira-agent-platform]] pipeline hits once it scales past one agent per ticket — LangGraph's conditional edges and fan-out give you the equivalent of ADK's `ParallelAgent` + join strategy here, so the reconciliation logic transfers either way.

## When you actually need a human

Wired as an explicit escalation signal rather than a special case in your orchestrator code:

| Trigger | Why it can't be automated away |
| --- | --- |
| Arbiter confidence below threshold | no reliable signal either output is correct |
| Critic-reviser loop hits max iterations without convergence | agents are stuck, more looping won't help |
| Tie in majority vote, no tiebreak rule | genuinely ambiguous |
| Tool-permission or policy violation | security boundary, not a quality judgment |
| Irreversible action (deploy, force-push, schema migration, delete) | cost of a wrong automated call is asymmetric |
| Output contains a secrets/credentials pattern | leak risk |
| Ticket/requirement itself is underspecified | agents can't invent acceptance criteria |
| Budget, token, or time limit exceeded | run is misbehaving, not just slow |

The diagram above shows this as a flow: coral is the automated arbitration step, amber is the human checkpoint — most runs never touch either box because the "no conflict" path bypasses them entirely.

## How agents actually get created and deployed

Two separate questions — definition and hosting.

### Definition

If your ADK version supports declarative Agent Config, skip hand-writing the YAML→Python loader in section 4 entirely:

```python
from google.adk.agents import Agent
from google.adk.tools import AgentTool

research_agent = Agent.from_config("agents/research-agent.yaml")  # declarative load

coder_agent = Agent(name="coder-agent", model="gemini-2.5-pro",
                     instruction=open("agents/coder-agent.md").read(),
                     tools=[read_file, write_file, run_tests])

coder_tool = AgentTool.create(coder_agent)  # coder is now callable by another agent

supervisor = Agent(name="supervisor", model="gemini-2.5-pro",
                    tools=[coder_tool], sub_agents=[reviewer_agent])
```

### Deployment

Since ADK deploys natively to more than one target:

| Target | Best for | Trade-off |
| --- | --- | --- |
| Cloud Run | fast start, per-request scaling, simplest ops | cold starts, request time limits |
| Vertex AI Agent Engine | ADK's native managed target — sessions/memory handled for you | less infra control, GCP-only |
| GKE | long-running workers, custom Python sandboxing, full control | most ops overhead — matches the Phase 6 scaling path in your doc |

## Test scenarios

| Category | Scenario | Pass criteria |
| --- | --- | --- |
| Registry validation | register an agent that references a disallowed tool | rejected outright, no partial registration |
| Single-agent | call research-agent with a known question | output matches schema, sources cited |
| Sequential workflow | collect → analyze → review → write | each step gets only its declared `input_from`, nothing else leaks through |
| Parallel workflow | security + performance + test reviewers on one PR | all three finish or time out independently; one failure doesn't kill the others (`fail_fast: false`) |
| Conflict injection | force reviewer to reject what coder approved | arbiter fires; if still unresolved, human gate fires |
| Fault injection | kill a tool call mid-run | retries per `max_retries`, then a clean failure — never a hang |
| Permission boundary | agent attempts a tool outside its allowlist | blocked before execution, logged, zero partial side effects |
| Regression | re-run last week's eval set after a prompt change | trajectory and response scores don't regress vs. baseline |

## Benchmarks

Split these into two layers — they answer different questions.

### Your pool's own metrics (what actually tells you if this system works)

| Metric | What it tells you |
| --- | --- |
| Task success rate | % of runs whose final output passes real acceptance criteria (tests, schema) |
| Trajectory / tool-use accuracy | did the agent call the right tools, in the right order, with the right args |
| Escalation rate | % of runs hitting the human gate — should trend down as prompts improve |
| Conflict rate | % of parallel/loop runs where sub-agents disagreed before arbitration |
| p50/p95 latency, cost per run | operational health |
| Rollback rate | % of agent versions rolled back after go-live |

### External reference benchmarks (useful for comparing base models, not for scoring your orchestration layer)

| Benchmark | Measures | Current signal (Sept 2026) |
| --- | --- | --- |
| SWE-bench Verified | resolving real GitHub issues, 500 human-checked tasks | Near-saturated at the frontier — top models cluster within about a point of each other around 95–96%, but treat this cautiously: the leaderboard is mostly self-reported, and an internal audit found flawed test cases among the hardest unsolved problems |
| SWE-bench Pro | contamination-resistant, harder real-world tasks | the standardized public-set leader sits around 59%, versus roughly 80% on the more permissive vendor-reported aggregate — that 20-35 point gap from Verified is the more honest read of current coding-agent capability |
| AgentBench, tau-bench, Terminal-Bench | tool-use, multi-turn tool-agent-user interaction, shell/terminal tasks | used alongside SWE-bench Verified as a standard four-benchmark suite specifically for evaluating agent frameworks, not just base models |
| ADK's own evaluator | trajectory match + response quality on an eval set you define | splits evaluation into analyzing the steps and tool choices an agent takes versus the quality of its final response, runnable through pytest or the `adk eval` CLI against JSON test-case files you write |

Public benchmarks score the underlying model, not your reconciliation layer or your escalation rules — those only get tested by an eval set built from your own Jira tickets: replay past resolved tickets through the pool, score by whether the agent's patch passes that ticket's actual test suite (not LLM judgment), and run it in CI on every prompt or workflow change. That's effectively your own private SWE-bench, and it's exactly what the ADK evaluator is designed to run continuously.

Happy to go deeper on any one piece next — the arbiter agent's prompt, the YAML registry schema, or a working `AgentTool` example wired to GitHub.