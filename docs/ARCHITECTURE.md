# Platform Architecture Baseline

## Executive Overview
The **Dynamic ADK Agent Platform** is not a static collection of scripted agents. It is an enterprise Agent Platform engineered to **dynamically discover, select, authorize, compose, execute, validate, and govern agents and tools**.

```
USER REQUEST
     │
     ▼
LLM TASK ANALYZER  (Selects semantic capabilities; NEVER endpoints/raw tools)
     │
     ▼
CAPABILITY RESOLVER
     ├── Agent Registry   (Authoritative catalog: capabilities, limits, approval)
     └── Tool Registry    (Discovered from MCP Registry / providers)
     │
     ▼
AGENT RESOLVER  (Validates enabled, authorized, compatible)
     │
     ▼
AGENT-AS-A-TOOL  (Dynamically wraps selected agents into tool interfaces)
     │
     ▼
ORCHESTRATOR  (Receives ONLY the scoped tools needed for the active task)
     │
     ├── Specialist Agent A  (Recommends)
     ├── Specialist Agent B  (Recommends)
     └── Specialist Agent C  (Recommends)
     │
     ▼
AGGREGATION & SYNTHESIS
     │
     ▼
CRITIC  (Challenges: detects constraint violations, boundary flaws)
     │
     ▼
REFINER  (Revises proposal based on specific critique)
     │
     ▼
DETERMINISTIC VALIDATION GUARDRAIL  (Mathematical & topological truth layer)
     │  States: FEASIBLE | OPTIMAL | UNPROVEN | IMPOSSIBLE
     ▼
FINAL DECISION  (Single Decision Owner: Orchestrator)
```

---

## Core Architectural Boundaries

### 1. Separation of Control Plane and Execution Plane
- **Control Plane (`registry-service`)**:
  - Independent FastAPI service backed by H2 via repository pattern.
  - Owns Agent Registry, MCP Server Registry, and Tool Registry.
  - Authoritative source of truth for runtime configurations, policy thresholds, and active status.
  - **Critical Boundary Rule**: The ADK application plane *never* connects directly to H2 or databases. All configuration reads and lifecycle updates occur via the REST Control Plane API.

- **Execution Plane (`app`)**:
  - ADK client and runtime engine.
  - Reads registry state through `RegistryClient` (fail-closed if registry unreachable).
  - Dynamically scopes the agent pool per task based on semantic capability requirements.

### 2. Capability-Based Decoupling
Agents and users never reference physical infrastructure or URLs:
- Agents express requirements as abstract capabilities:
  ```python
  requirements = ["route_optimization", "constraint_reasoning"]
  ```
- The **Capability Resolver** maps capabilities through the Tool and MCP Registries to real providers (e.g., `route_optimization -> Solver MCP` today; `route_optimization -> Gurobi Service` tomorrow) without changing agent prompt or logic.

### 3. Agent-as-a-Tool Dynamic Scoping
- The Orchestrator does not hold an open connection to all potential agents in the universe.
- For each task, the Agent Resolver loads *only* the authorized, compatible, and enabled agents matching the task's required capabilities.
- Each specialist is dynamically wrapped as an `AgentAsTool` callable interface.

### 4. Deterministic Validation Guardrail & Grounded Truth
- Large Language Models are treated as probabilistic recommendation generators.
- LLMs are **never trusted** for mathematical optimality, Hamiltonian cycle validity, or topological ordering proofs.
- All proposals pass through the **Deterministic Validation Guardrail**, maintaining strictly distinct states:
  - `FEASIBLE`: Satisfies all hard constraints.
  - `OPTIMAL`: Feasible and proven minimal through exhaustive enumeration or mathematical proof.
  - `UNPROVEN`: Feasible, but solved heuristically (e.g., n=15 factorial TSP or 2-opt); optimality is explicitly reported as unproven.
  - `IMPOSSIBLE`: Formally proven impossible (e.g., disconnected graph components or circular dependency cycles); the system abstains rather than hallucinating.

### 5. Single Decision Owner Doctrine
- **Specialists** recommend.
- **Critic** challenges.
- **Refiner** revises.
- **Orchestrator** makes the single binding decision.
- Competing or split-brain decision makers are architecturally disallowed.

---

## Baseline Regression Rule
The current 10-problem routing benchmark (`app/solver/problems.py`, `tests/unit/test_solver.py`) is the permanent golden regression baseline:
1. Triangle (3 cities)
2. Square Matrix (4 cities)
3. Linear Highway (4 cities)
4. Asymmetric One-Way (5 cities)
5. Morning Hub Constraint (6 cities)
6. Hub-and-Spoke (7 cities)
7. 15-City Factorial (combinatorial pruning, `FEASIBLE` / `UNPROVEN`)
8. VRP Split (capacity partitioned, `FEASIBLE` / `UNPROVEN`)
9. Disconnected Island (`IMPOSSIBLE` / abstention)
10. Time-Paradox Precedence (`IMPOSSIBLE` / circular dependency detected)

All 10 benchmark problems remain 100% green and deterministic throughout platform evolution.
