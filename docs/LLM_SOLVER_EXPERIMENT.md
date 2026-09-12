# LLM Solver Experiment — gpt-oss-20b on Problems 1–10

Pool agents were pointed at a **hosted OpenAI-compatible LLM** (`openai/gpt-oss-20b`, NVIDIA
`integrate.api.nvidia.com`, temperature 0.0) instead of the deterministic solver. This measures
raw-model fidelity and whether grounding (RAG or toolcheck) is required. The requested
`openai/gpt-oss-120b` id returned HTTP 410 (not provisioned for the key), so the 20B variant was
used; ~2.5 s/response, all 10 problems completed well under the API timeouts.

| # | Problem | LLM string PASS | Grounded order | LLM cost | Optimum | Strike | Time (ms) | Deterministic across runs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Global Shopping (5 cities) | PASS | A->B->C->D->E->A | 45.0 | 45.0 | OK | 10493 | no (costs stable) |
| 2 | Warehouse Routing (5 cities) | PASS | A->B->D->E->C->A | 40.0 | 40.0 | OK | 10396 | single run |
| 3 | Time-Window Delivery (6 cities) | PASS | A->B->F->C->D->E->A | 60.0 | 60.0 | OK | 20332 | single run |
| 4 | Directional Delivery (5 cities) | PASS | A->B->E->C->D->A | 25.0 | 25.0 | OK | 46214 | no (costs stable) |
| 5 | Priority Dispatch (6 cities) | PASS | A->B->C->D->F->E->A | 60.0 | 60.0 | OK | 9463 | single run |
| 6 | Map Revisit (6 cities, first-stop rule) | PASS | A->B->F->E->D->C->A | 110.0 | 110.0 | OK | 57388 | single run |
| 7 | 15-City Factorial | PASS | none (adjacency dump, no tour) | None | None | FAIL | 22334 | single run |
| 8 | VRP Split (2 vehicles, 10 cities) | PASS | none (specialists returned no route) | None | None | FAIL | 36028 | single run |
| 9 | Impossibility (4 cities) | PASS | impossible called correctly | None | None | OK | 16140 | no (wording differs) |
| 10 | Circular Precedence | PASS | circular dependency detected | None | None | OK | 4685 | yes |

## Verdict

- Problems with exact optimal cost found by the raw model: **6/8 solvable** (P1–P6 all hit the
  optimum on the first try; only P7/P8 could not be grounded into a tour).
- Raw string-based PASS count: **10/10** — every problem ended with an accepted agent proposal.
- Determinism (temperature 0): decisions across repeated runs are **not identical** for the
  hosted endpoint (P1, P4, P9 cases), though the reproduced costs stayed at the optimum. Pure
  string-level determinism therefore cannot be relied on; the deterministic tour engine is what
  guarantees the project determinism contract.
- RAG verdict: raw gpt-oss-20b nails small symmetric TSPs and correctly abstains on the
  impossibilities, but degrades on large/VRP-style cases unless the plan/route is computed by
  deterministic tools. Beads 7–9 should keep the **tool-grounded solver** as the decision layer
  and use the LLM for synthesis/free-text planning (the "research"/"review" agents), with repo
  RAG over the problem spec for context — exactly the split the framework already enforces.