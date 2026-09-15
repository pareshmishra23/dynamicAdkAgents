# Decision Ownership & Deterministic Validation Guardrails

## The Core Philosophy
In an agentic architecture, unbounded autonomy without deterministic guardrails leads to:
1. Competing decisions between specialists with no clear tiebreaker.
2. Unchecked hallucinations regarding mathematical or constraint proofs.
3. Silent failures where impossible tasks produce plausible-sounding but invalid solutions.

The Dynamic ADK Agent Platform solves this with **Single Decision Ownership** and **Deterministic Validation Guardrails**.

---

## 1. Single Decision Owner Model

```
                    ORCHESTRATOR (Decision Owner)
                               │
         ┌─────────────────────┼─────────────────────┐
         ▼                     ▼                     ▼
    Specialist A          Specialist B          Specialist C
  (Recommendation)      (Recommendation)      (Recommendation)
         │                     │                     │
         └─────────────────────┼─────────────────────┘
                               ▼
                    Aggregation & Synthesis
                               │
                               ▼
                             CRITIC
                     (Challenges & Questions)
                               │
                               ▼
                            REFINER
                    (Iterative Revision Loop)
                               │
                               ▼
                 DETERMINISTIC GUARDRAILS
             (Checks topology, constraints, bounds)
                               │
                               ▼
                         FINAL DECISION
```

### Responsibility Contracts
| Actor | Responsibility | Authority Level |
|---|---|---|
| **Specialist Agents** | Inspect subproblems, execute domain tools, and propose domain recommendations. | Recommender (No decision authority) |
| **Critic** | Evaluates aggregated recommendations against hard constraints, budgets, and safety criteria. Generates targeted critique questions. | Quality Gate (Can reject proposals, cannot decide) |
| **Refiner** | Revises proposals to directly resolve the Critic's specific questions within bounded iteration limits. | Editor (Proposes adjustments) |
| **Deterministic Guardrail** | Algorithmic and mathematical validation layer (Hamiltonian cycle check, capacity check, cycle detector). | Verifier of Truth (Veto power) |
| **Orchestrator** | Synthesizes specialist output, drives critique/refinement loops, applies guardrails, and renders the single binding decision. | **Sole Decision Owner** |

**Rule**: No specialist agent ever writes or returns the final platform decision directly. There are no peer voting compromises or split decisions.

---

## 2. Deterministic Validation Guardrails

Large Language Models cannot be trusted for mathematical, combinatorial, or topological guarantees.

### 2.1 The Validation Pipeline
Before any proposed decision is finalized, it passes through deterministic validators:
1. **Hamiltonian Completeness**: Did the route visit every required node exactly once and return to origin?
2. **Hard Constraint Satisfaction**: Are specific first-stop, time-window, or precedence constraints satisfied?
3. **Graph Connectivity**: Does an edge actually exist for every traversal in the route?
4. **Dependency Cycles**: Does Kahn's topological sort or cycle detection find circular ordering constraints?
5. **Vehicle Capacity**: In VRP splits, does any vehicle exceed its designated stop/weight limit?

### 2.2 Four Distinct Optimization States
The platform explicitly enforces four mutually exclusive states:

1. `FEASIBLE`:
   - All physical, ordering, and capacity constraints are proven satisfied.
2. `OPTIMAL`:
   - The solution is feasible AND mathematically proven to be the absolute global minimum (via complete branch-and-bound, exhaustive loop enumeration, or integer programming certificate).
3. `UNPROVEN`:
   - The solution is feasible, but derived through heuristics (e.g. 2-opt or nearest neighbor on 15+ cities).
   - **Critical Mandate**: `FEASIBLE != OPTIMAL`. The system must never label a heuristic solution as optimal. It reports `UNPROVEN` with the best-known upper bound.
4. `IMPOSSIBLE`:
   - The problem is mathematically or topologically infeasible (e.g., disconnected island or circular dependency $A \to B \to C \to A$).
   - **Explicit Abstention**: The system explicitly halts, reports impossibility, and abstains from producing a hallucinated solution.

---

## 3. Bounded Reasoning & Abstention
- Refinement loops are strictly bounded by iteration limits (default: 3 iterations).
- If the Critic and Refiner cannot resolve constraint issues within the bound, the platform halts with an explicit `abstain_human_review` status.
- It never loops infinitely or produces an unverified guess.
