# Dynamic ADK Agents

A local learning and interview platform demonstrating a configuration-driven agent registry, dynamic routing, Agent-as-a-Tool adapters, sequential and parallel orchestration, and a bounded critic/refiner loop.

## Architecture

```text
User Request
    |
    v
Router / Task Analyzer
    |
    v
Agent Registry -> Dynamic Resolver -> Agent-as-a-Tool adapters
    |
    v
Orchestrator (single final decision owner)
    |\
    | +-- parallel specialist execution
    +---- sequential integration
    |
    v
Critic -> Refiner -> bounded validation loop
```

## Registry control plane (Bead 1)

`registry-service/` contains a standalone **FastAPI + H2** control plane that owns
Agent and MCP configuration for the pool. The ADK app never hard-codes servers or
touches H2 — it will ask the registry via a client (Bead 2). See
[`registry-service/README.md`](registry-service/README.md) for setup, the REST API,
and fully local tests (no Gemini).

## Concepts

- **Agent:** a reusable reasoning specialist defined in `config/agents.yaml`.
- **Agent-as-a-Tool:** a selected agent wrapped as a callable capability for the orchestrator.
- **Tool:** a deterministic function exposed to an agent; tools should be explicitly allowlisted.
- **MCP:** an integration boundary for external tools and services. MCP can be added behind the tool registry without making every agent depend on it.
- **Router:** determines which capabilities are required. It does not execute specialists.
- **Orchestrator:** delegates, integrates, and owns the final decision.
- **Critic/Refiner:** challenges and revises a proposal with a hard maximum of three iterations.

## Setup

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
```

The current local foundation only needs PyYAML and pytest. Google ADK can be installed separately when the real Gemini adapter is added:

```bash
python -m pip install -e '.[adk]'
```

Set credentials only in an ignored `.env` file when enabling the optional Gemini integration. Never commit or print `GOOGLE_API_KEY`.

## Run tests

```bash
python -m pytest
```

The tests are deterministic and do not consume Gemini quota. BDD feature files are in `features/`; pytest-bdd step bindings will be added in the next implementation checkpoint.

## Run the demo

```bash
python -m app
```

The demo uses deterministic local specialist adapters. The adapter seam in `app/agents/factory.py` is where a Google ADK model-backed implementation can be added without changing registry or orchestration behavior.

## Current implementation status

Completed checkpoints:

- Externalized YAML configuration and typed agent definitions.
- Five reusable specialist definitions.
- Registry lookup, capability search, version metadata, and disabled-agent protection.
- On-demand resolver.
- Structured routing validation.
- Agent-as-a-Tool adapter.
- Parallel and sequential execution.
- Bounded critic/refiner loop.
- Unit tests and local CLI demo.

Next checkpoint: bind the BDD features, add optional ADK integration behind an environment guard, and preserve MCP examples if an existing source repository is provided.
