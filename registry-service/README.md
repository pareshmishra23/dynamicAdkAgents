# Registry Service — FastAPI Control Plane + H2

Bead 1 of the dynamic ADK agents build. A self-contained registry service that owns
**Agent / MCP / Tool configuration** through REST APIs with **H2** as the persistence
store. It is the single control plane the ADK application talks to — the ADK app must
**never** hard-code servers or reach H2 directly.

```text
FastAPI
   |
   v
Service Layer
   |
   v
Repository Layer
   |
   v
H2
```

## Layout

```text
registry-service/
├── app/
│   ├── main.py              # FastAPI app factory + wiring
│   ├── config/              # settings + H2 jar bootstrap
│   ├── api/                 # REST routes + dependency injection
│   ├── service/             # business rules (duplicates, enable/disable, timestamps)
│   ├── repository/          # H2 JDBC access (real H2 via JayDeBeApi)
│   └── model/               # domain models (Pydantic)
├── features/                # Gherkin BDD specs (MCP + Agent registry)
├── scripts/                 # utility to fetch the H2 jar
├── tests/
│   ├── unit/                # repository, service, API tests (in-memory H2)
│   └── bdd/                 # pytest-bdd bindings
└── README.md
```

## Why H2 via JDBC

H2 is a Java database. This service connects to it over JDBC using
`jaydebeapi` + `JPype1`, which launches an embedded JVM on the host.
The H2 driver jar is auto-downloaded from Maven Central on first use
(`app/config/h2jar.py`).

- **Dev:** file-backed database — `jdbc:h2:file:./data/registry`
- **Tests:** real H2 in-memory instances — `jdbc:h2:mem:<uuid>`

Everything runs locally: **no Gemini, no cloud, no Docker needed.**

## Setup

Needs Python 3.11–3.13 (JPype1 wheels) and a local JDK 11+.

```bash
cd registry-service
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
```

## Run

```bash
python -m app                 # starts uvicorn on 127.0.0.1:8000
```

Overrides via environment variables (see `.env.example`): `H2_URL`, `H2_USER`,
`H2_PASSWORD`, `H2_JAR_PATH`, `HOST`, `PORT`.

Interactive docs: http://127.0.0.1:8000/docs

## Run tests

```bash
python -m pytest              # 52 tests: unit + BDD, all against real in-memory H2
```

### BDD scenarios

`features/mcp_registry.feature`

- Register MCP server
- Retrieve registered MCP server
- Disable MCP server
- Enable MCP server
- Delete MCP server
- Reject duplicate MCP server
- Do not return disabled server as active

`features/agent_registry.feature`

- Register agent
- Retrieve agent
- Disable agent
- Enable agent
- Delete agent
- Reject duplicate agent

## REST API

Versioned under `/api/v1`.

### MCP servers

| Method | Path | Description |
| --- | --- | --- |
| POST | `/api/v1/mcp-servers` | Register an MCP server (409 if duplicate id) |
| GET | `/api/v1/mcp-servers` | List servers; `?enabled=true\|false` filters |
| GET | `/api/v1/mcp-servers/{id}` | Retrieve one server |
| PUT | `/api/v1/mcp-servers/{id}` | Replace configurable fields |
| PATCH | `/api/v1/mcp-servers/{id}/enable` | Mark enabled |
| PATCH | `/api/v1/mcp-servers/{id}/disable` | Mark disabled |
| DELETE | `/api/v1/mcp-servers/{id}` | Remove (404 if unknown) |

`mcp_server` fields: `id`, `name`, `description`, `endpoint`, `transport`,
`enabled`, `version`, `created_at`, `updated_at`.

### Agents

| Method | Path | Description |
| --- | --- | --- |
| POST | `/api/v1/agents` | Register an agent (409 if duplicate id) |
| GET | `/api/v1/agents` | List agents; `?enabled=true\|false` filters |
| GET | `/api/v1/agents/{id}` | Retrieve one agent |
| PUT | `/api/v1/agents/{id}` | Replace fields |
| PATCH | `/api/v1/agents/{id}/enable` | Mark enabled |
| PATCH | `/api/v1/agents/{id}/disable` | Mark disabled |
| DELETE | `/api/v1/agents/{id}` | Remove (404 if unknown) |

`agent` fields: `id`, `name`, `description`, `capability`, `model`, `enabled`,
`config`, `policy`, `output_contract`, `requires_human_approval`, `created_at`,
`updated_at`.

`policy` is the determinism/runtime contract: `temperature` (default `0.0`),
`seed`, `timeout_seconds`, `max_tool_calls`, `max_retries`, `max_iterations`.
Defaults are deterministic (greedy, bounded, fail-closed). See
[`docs/RUNTIME_POLICY.md`](../docs/RUNTIME_POLICY.md) for the full contract.

`output_contract` (optional) is the expected decisive output shape: `type`,
`required` properties. `requires_human_approval` (default `false`) marks an agent
that must pause for human approval before it may execute; the orchestrator gates on
it (see the HITL section of `docs/RUNTIME_POLICY.md`).

### Example

```bash
curl -s -X POST localhost:8000/api/v1/mcp-servers \
  -H 'content-type: application/json' \
  -d '{"id":"taxi-tools","name":"Taxi Tools","endpoint":"stdio://taxi","transport":"stdio"}'

curl -s 'localhost:8000/api/v1/mcp-servers?enabled=true'
curl -s -X PATCH localhost:8000/api/v1/mcp-servers/taxi-tools/disable
```

## Architecture rule

No hard-coded MCP server list in the ADK application:

```text
Bad:   mcp_servers = ["taxi-tools", "car-tools", "travel-tools"]
Good:  ADK → Registry Client → FastAPI Registry → H2
```

The ADK application asks *"Which enabled MCP servers/capabilities are currently
registered?"* — the Registry Client does that in Bead 2.

## Troubleshooting

- **JVM start failures** — ensure a JDK is on the path (`java -version`).
- **`H2_JAR_PATH`** — set it to a pre-downloaded jar to avoid network on first run.
- **Tests hit the slow path once** — the JVM boots once per pytest session.