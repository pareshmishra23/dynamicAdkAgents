# Registry Architecture & Control Plane Specification

## Overview
The Registry Control Plane is the authoritative runtime catalog for the dynamic agent platform. It decouples agent definition, tool provisioning, and server topology from application source code.

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Control Plane                    │
│                                                             │
│   POST/GET/PUT/PATCH/DELETE      GET/POST/PATCH/DELETE      │
│        /api/v1/agents               /api/v1/tools           │
│              ▲                            ▲                 │
│              │                            │                 │
│              └──────────────┬─────────────┘                 │
│                             │                               │
│              GET/POST/PUT/PATCH/DELETE                      │
│                  /api/v1/mcp-servers                        │
└─────────────────────────────┼───────────────────────────────┘
                              ▼
                 Service Layer (Business Logic)
                              ▼
             Repository Layer (SQL / JayDeBeApi)
                              ▼
                     H2 Embedded Database
                              ▲
                              │  (STRICT ISOLATION:
                              │   ADK never accesses directly)
                              │
                    ┌─────────────────┐
                    │ ADK Application │
                    │ RegistryClient  │
                    └─────────────────┘
```

---

## 1. Registry Domain Ownership

The Registry Control Plane owns three entities:

### 1.1 Agent Registry
- **Role**: Maintains definition, version, model configuration, capability tags, policy bounds, and human-in-the-loop flags for all agents.
- **Authoritative Schema**:
  ```json
  {
    "id": "route-optimizer",
    "name": "Route Optimizer",
    "description": "Optimizes constrained routes",
    "capabilities": ["route_optimization", "constraint_reasoning"],
    "model": "gemini-flash-latest",
    "enabled": true,
    "version": "1.0",
    "policy": {
      "timeout_seconds": 30,
      "max_tool_calls": 10
    },
    "output_contract": {
      "type": "object",
      "required": ["solution"]
    },
    "requires_human_approval": false
  }
  ```
- **Critical Invariant**: There is NO static hardcoded `AGENTS = { ... }` in the Python application acting as authoritative state. The database/API is the sole authority.

### 1.2 MCP Registry
- **Role**: Maintains active Model Context Protocol (MCP) server endpoints and transport specifications.
- **Authoritative Schema**:
  ```json
  {
    "id": "solver-mcp",
    "name": "Solver MCP",
    "endpoint": "http://localhost:7101",
    "transport": "http",
    "enabled": true,
    "version": "1.0",
    "description": "Dedicated mathematical combinatorial solver"
  }
  ```
- **Operations**: `ADD`, `GET`, `UPDATE`, `ENABLE`, `DISABLE`, `DELETE`.

### 1.3 Tool Registry
- **Role**: Maintains available tools discovered from MCP servers or registered directly by capability.
- **Authoritative Schema**:
  ```json
  {
    "tool_id": "matrix_build",
    "name": "Matrix Builder",
    "description": "Constructs distance and cost matrices across coordinate spaces",
    "capability": "graph_analysis",
    "provider": "solver-mcp",
    "enabled": true
  }
  ```
- **Operations**: `ADD`, `GET`, `UPDATE`, `ENABLE`, `DISABLE`, `DELETE`.

---

## 2. Layering and Persistence
The control plane strictly enforces three tiers:
1. **API Layer (`app/api`)**: FastAPI route controllers handling validation, response models, HTTP status codes, and query filtering (`?enabled=true`, `?capability=...`).
2. **Service Layer (`app/service`)**: Domain validation, conflict detection (preventing duplicate IDs), and enable/disable toggle logic.
3. **Repository Layer (`app/repository`)**: Pure SQL persistence via JDBC connection pool to H2.

---

## 3. Storage & Isolation Contract
- **No Direct ADK Database Access**: The ADK application plane communicates exclusively over HTTP with the FastAPI Registry endpoints using `RegistryClient`.
- **Fail-Closed Contract**: If the Registry Control Plane is unreachable or returns HTTP errors, the ADK application fails closed with explicit `RegistryUnavailable` or `RoutingError` exceptions. It never silently creates fictitious or unverified agents.
- **Dynamic Updates Without Redeployment**: Creating an agent via `POST /api/v1/agents` or disabling one via `PATCH /api/v1/agents/{id}/disable` immediately alters subsequent routing and capability resolution without requiring restart of either service.
