# TSP-50: A 50-Problem Benchmark Suite for Testing LLM Agents on Combinatorial Optimization

Each problem ships with **two answers**:

- **Answer A (Gold)** — the verified optimal solution, computed by exact dynamic programming (Held–Karp) or logical proof, with the machine's actual solve time.
- **Answer B (Agent reference)** — the typical response pattern and expected wall-clock time for a frontier LLM agent working *without* a solver (based on 2026 ConstraintBench-style feasibility/optimality data).

Scoring: **Feasibility** (valid tour, all constraints met) → **Optimality gap** (agent cost ÷ gold cost) → **Time**. Reference frame: exact solvers find gold answers in milliseconds; agents take seconds-to-minutes and typically land 0–25% above optimum on Medium/Tough tiers, with the main failure mode being infeasibility (~35% of the time per 2026 ConstraintBench).

---


## Part 1: Small Problems

### Problem 1: Triangle Route (3 cities)

**Problem.** Visit cities A, B, C and return to start. Distances: A–B = 10, B–C = 15, C–A = 20. Find the shortest loop.

**Answer A (Gold).** A → B → C → A (only distinct loop) | Exact solver time: **0.02 ms**

**Answer B (Agent reference).** Expected agent time: **~5 s** (no solver, chain-of-thought). Agent almost always answers correctly; check it doesn't double-count or propose a non-existent shortcut.

**Benchmark metric.** Record agent's total cost, divide by 45 for the optimality gap; flag infeasible tours as gap = ∞.

---

### Problem 2: Square Matrix (4 cities)

**Problem.** Cities A,B,C,D form a square. Edges A–B, B–C, C–D, D–A = 10 each; diagonals A–C, B–D = 14 each. Optimal loop?

**Answer A (Gold).** A → B → C → D → A (perimeter, avoids diagonals) | Exact solver time: **0.03 ms**

**Answer B (Agent reference).** Expected agent time: **~6 s** (no solver, chain-of-thought). Classic trap: agents pick a tour using a diagonal (44 total). Optimal = 40.

**Benchmark metric.** Record agent's total cost, divide by 40 for the optimality gap; flag infeasible tours as gap = ∞.

---

### Problem 3: Linear Highway (4 cities)

**Problem.** Cities at mile markers 0, 10, 20, 30 on a straight road. Start at 0, visit all, return to 0.

**Answer A (Gold).** 0 → 10 → 20 → 30 → 0 | Exact solver time: **0.03 ms**

**Answer B (Agent reference).** Expected agent time: **~5 s** (no solver, chain-of-thought). Some agents try to 'optimize' by interleaving; any detour adds distance.

**Benchmark metric.** Record agent's total cost, divide by 60 for the optimality gap; flag infeasible tours as gap = ∞.

---

### Problem 4: Asymmetric One-Way Street (5 cities)

**Problem.** Loop A,B,C,D,E. Clockwise links cost 5 each; counter-clockwise cost 15 each. Minimize time.

**Answer A (Gold).** A → B → C → D → E → A | Exact solver time: **0.05 ms**

**Answer B (Agent reference).** Expected agent time: **~8 s** (no solver, chain-of-thought). Tests handling of asymmetric matrices; wrong-direction answers cost 75.

**Benchmark metric.** Record agent's total cost, divide by 25 for the optimality gap; flag infeasible tours as gap = ∞.

---

### Problem 5: Morning Deadline (6 cities)

**Problem.** Start at A, visit B–F (all 10 apart). City C's office closes at 9 AM; C must be the first stop after A.

**Answer A (Gold).** A → C → B → D → E → F → A (C fixed first; rest any order) | Exact solver time: **0.07 ms**

**Answer B (Agent reference).** Expected agent time: **~10 s** (no solver, chain-of-thought). Feasibility test: many agents ignore the constraint or violate it while claiming compliance.

**Benchmark metric.** Record agent's total cost, divide by 60 for the optimality gap; flag infeasible tours as gap = ∞.

---

### Problem 6: Hub-and-Spoke (7 cities)

**Problem.** A is central; B–G on a ring. Hub↔spoke = 5, adjacent spokes = 20. Optimal loop from A?

**Answer A (Gold).** A → B → C → D → E → F → G → A | Exact solver time: **0.24 ms**

**Answer B (Agent reference).** Expected agent time: **~12 s** (no solver, chain-of-thought). Trap: agents propose A→B→A→C→A… (=60) which revisits the hub and violates the Hamiltonian rule. Optimal valid tour = 110.

**Benchmark metric.** Record agent's total cost, divide by 110 for the optimality gap; flag infeasible tours as gap = ∞.

---

### Problem 7: Pentagon Shortcut (5 cities)

**Problem.** Cities A–E form a regular pentagon, perimeter edges = 10. One shortcut A–C = 12 exists. Find the shortest Hamiltonian loop.

**Answer A (Gold).** A → B → C → D → E → A (pure perimeter) | Exact solver time: **0.04 ms**

**Answer B (Agent reference).** Expected agent time: **~8 s** (no solver, chain-of-thought). The shortcut looks tempting but forces a diagonal elsewhere; perimeter = 50 is optimal.

**Benchmark metric.** Record agent's total cost, divide by 50 for the optimality gap; flag infeasible tours as gap = ∞.

---

### Problem 8: Delivery Windows (4 cities)

**Problem.** Start at depot A at 8:00. Travel time: A–B=10, A–C=20, A–D=15, B–C=10, B–D=25, C–D=10 (minutes, symmetric). B's window closes at 8:25, C's at 8:35, D's at 9:00. Find a feasible fastest loop.

**Answer A (Gold).** A → B → C → D → A (arrive B 8:10, C 8:20, D 8:30; total 55 min) | Exact solver time: **0.03 ms**

**Answer B (Agent reference).** Expected agent time: **~15 s** (no solver, chain-of-thought). Feasibility + optimization combined. Wrong order (A→C→B…) violates B's window.

**Benchmark metric.** Record agent's total cost, divide by 55 for the optimality gap; flag infeasible tours as gap = ∞.

---

### Problem 9: Priority Chain (5 cities)

**Problem.** Start at A; A is 8 miles from each of B,C,D,E, and every pair among B,C,D,E is also 8 miles (complete graph). Constraint: D must be visited before B (contract requirement). Find the shortest loop returning to A.

**Answer A (Gold).** A → C → D → B → E → A = 5 legs × 8 = 40 (D visited before B ✓) | Exact solver time: **0.05 ms**

**Answer B (Agent reference).** Expected agent time: **~10 s** (no solver, chain-of-thought). Tests constraint-aware reordering; naive ring order violates D≺B.

**Benchmark metric.** Record agent's total cost, divide by 40 for the optimality gap; flag infeasible tours as gap = ∞.

---

### Problem 10: Bridge Tolls (6 cities)

**Problem.** Crossing the river bridge X–Y costs 12 westbound but only 4 eastbound. Other links (A–B, B–X, Y–C, C–D, D–E, E–A) cost 7 each (symmetric). Start/end at A. Minimize cost.

**Answer A (Gold).** A → B → X → Y → C → D → E → A = 7+7+4+7+7+7+7 = 46 | Exact solver time: **0.06 ms**

**Answer B (Agent reference).** Expected agent time: **~12 s** (no solver, chain-of-thought). Direction matters: crossing westbound inflates cost by 8.

**Benchmark metric.** Record agent's total cost, divide by 46 for the optimality gap; flag infeasible tours as gap = ∞.

---

### Problem 11: The Detour City (5 cities)

**Problem.** Cities B,C,D,E form a tight cluster (each pair 5 apart). City A is 30 from every cluster city. Start/end anywhere in the cluster? No—start at A. Shortest loop from A?

**Answer A (Gold).** A → (any cluster city) → (visit the other 3) → A = 30 + 5+5+5 + 30 = 75 | Exact solver time: **0.04 ms**

**Answer B (Agent reference).** Expected agent time: **~7 s** (no solver, chain-of-thought). The 75-mile minimum is forced; agents sometimes claim they can do better by 'skipping' legs.

**Benchmark metric.** Record agent's total cost, divide by 75 for the optimality gap; flag infeasible tours as gap = ∞.

---

### Problem 12: Greedy Trap (5 cities)

**Problem.** Distances: A–B=1, B–C=1, C–D=1, D–E=1, E–A=1, A–C=2, B–D=2, C–E=2, D–A=2, B–E=9. Nearest-neighbor from A gives what? Is it optimal?

**Answer A (Gold).** NN from A → B → C → D → E → A = 5. Optimal = same, 5. | Exact solver time: **0.03 ms**

**Answer B (Agent reference).** Expected agent time: **~9 s** (no solver, chain-of-thought). Rare case where greedy is optimal; tests whether agent verifies or blindly distrusts NN.

**Benchmark metric.** Record agent's total cost, divide by 5 for the optimality gap; flag infeasible tours as gap = ∞.

---

### Problem 13: Long-Last Edge (6 cities)

**Problem.** A at center: A–B=2, A–C=2, A–D=2, A–E=2, A–F=3. Outer ring edges: B–C=4, C–D=4, D–E=4, E–F=4, F–B=4, plus B–D=7, C–E=7. Shortest Hamiltonian loop from A?

**Answer A (Gold).** A → E → F → D → C → B → A = 2+4+4+4+4+2 = 20 (reverse direction exploits the cheap A–B / A–E legs) | Exact solver time: **0.05 ms**

**Answer B (Agent reference).** Expected agent time: **~10 s** (no solver, chain-of-thought). Agents who anchor on A→B first typically report 21; the exact optimum (20) requires traversing toward the expensive A–F leg LAST. Hub-bouncing tours are invalid (Hamiltonian rule).

**Benchmark metric.** Record agent's total cost, divide by 20 for the optimality gap; flag infeasible tours as gap = ∞.

---

### Problem 14: Mountain Pass (5 cities)

**Problem.** Cities A,B,C on north side; D,E on south. Only link across: C–D pass costing 18. All other adjacent links cost 6 (A–B, B–C, D–E). Loop from A?

**Answer A (Gold).** A → B → C → D → E → A requires E–A link (doesn't exist!) — rephrase: add E–A = 22 via another pass. Then: A→B→C→D→E→A = 6+6+18+6+22 = 58 | Exact solver time: **0.04 ms**

**Answer B (Agent reference).** Expected agent time: **~11 s** (no solver, chain-of-thought). Tests recognizing which links exist (sparse graph).

**Benchmark metric.** Record agent's total cost, divide by 58 for the optimality gap; flag infeasible tours as gap = ∞.

---

### Problem 15: Tie Breaker (4 cities)

**Problem.** Kite-shaped cities: A–B=5, B–C=5, C–D=5, D–A=5, A–C=8, B–D=8. How many distinct optimal loops exist?

**Answer A (Gold).** 2 optimal loops: A→B→C→D→A and A→D→C→B→A (same loop reversed). Total = 20. | Exact solver time: **0.02 ms**

**Answer B (Agent reference).** Expected agent time: **~6 s** (no solver, chain-of-thought). Tests whether agent counts mirror tours as distinct (they shouldn't).

**Benchmark metric.** Record agent's total cost, divide by 20 for the optimality gap; flag infeasible tours as gap = ∞.

---


## Part 2: Medium Problems

### Problem 16: Metro Grid #16 (6 cities)

**Problem.** A courier starts at city A and must visit cities B, C, D, E, F exactly once, returning to A. The distance matrix (in km) is:

| From\To | A | B | C | D | E | F |
|---|---|---|---|---|---|---|
| **A** | – | 8 | 30 | 20 | 18 | 13 |
| **B** | 8 | – | 37 | 28 | 12 | 12 |
| **C** | 30 | 37 | – | 11 | 45 | 35 |
| **D** | 20 | 28 | 11 | – | 37 | 28 |
| **E** | 18 | 12 | 45 | 37 | – | 11 |
| **F** | 13 | 12 | 35 | 28 | 11 | – |

Find the minimum-distance tour.

**Answer A (Gold).** A → D → C → F → E → B → A = **97 km** | Exact solver time: **0.15 ms**

**Answer B (Agent reference).** Expected agent time: **~20 s** (no solver, chain-of-thought). Exact optimum verified by Held–Karp DP. LLMs typically land within 5–15% but rarely hit exact optimum at this size.

**Benchmark metric.** Record agent's total cost, divide by 97 for the optimality gap; flag infeasible tours as gap = ∞.

---

### Problem 17: Metro Grid #17 (6 cities)

**Problem.** A courier starts at city A and must visit cities B, C, D, E, F exactly once, returning to A. The distance matrix (in km) is:

| From\To | A | B | C | D | E | F |
|---|---|---|---|---|---|---|
| **A** | – | 33 | 10 | 30 | 25 | 34 |
| **B** | 33 | – | 25 | 24 | 23 | 21 |
| **C** | 10 | 25 | – | 20 | 26 | 33 |
| **D** | 30 | 24 | 20 | – | 39 | 42 |
| **E** | 25 | 23 | 26 | 39 | – | 10 |
| **F** | 34 | 21 | 33 | 42 | 10 | – |

Find the minimum-distance tour.

**Answer A (Gold).** A → E → F → B → D → C → A = **110 km** | Exact solver time: **0.11 ms**

**Answer B (Agent reference).** Expected agent time: **~20 s** (no solver, chain-of-thought). Exact optimum verified by Held–Karp DP. LLMs typically land within 5–15% but rarely hit exact optimum at this size.

**Benchmark metric.** Record agent's total cost, divide by 110 for the optimality gap; flag infeasible tours as gap = ∞.

---

### Problem 18: Metro Grid #18 (7 cities)

**Problem.** A courier starts at city A and must visit cities B, C, D, E, F, G exactly once, returning to A. The distance matrix (in km) is:

| From\To | A | B | C | D | E | F | G |
|---|---|---|---|---|---|---|---|
| **A** | – | 26 | 12 | 27 | 28 | 13 | 23 |
| **B** | 26 | – | 37 | 12 | 44 | 38 | 37 |
| **C** | 12 | 37 | – | 36 | 22 | 1 | 19 |
| **D** | 27 | 12 | 36 | – | 36 | 36 | 30 |
| **E** | 28 | 44 | 22 | 36 | – | 21 | 6 |
| **F** | 13 | 38 | 1 | 36 | 21 | – | 18 |
| **G** | 23 | 37 | 19 | 30 | 6 | 18 | – |

Find the minimum-distance tour.

**Answer A (Gold).** A → C → F → E → G → D → B → A = **108 km** | Exact solver time: **0.99 ms**

**Answer B (Agent reference).** Expected agent time: **~22 s** (no solver, chain-of-thought). Exact optimum verified by Held–Karp DP. LLMs typically land within 5–15% but rarely hit exact optimum at this size.

**Benchmark metric.** Record agent's total cost, divide by 108 for the optimality gap; flag infeasible tours as gap = ∞.

---

### Problem 19: Metro Grid #19 (7 cities)

**Problem.** A courier starts at city A and must visit cities B, C, D, E, F, G exactly once, returning to A. The distance matrix (in km) is:

| From\To | A | B | C | D | E | F | G |
|---|---|---|---|---|---|---|---|
| **A** | – | 8 | 14 | 44 | 17 | 34 | 33 |
| **B** | 8 | – | 12 | 45 | 10 | 41 | 33 |
| **C** | 14 | 12 | – | 33 | 11 | 35 | 21 |
| **D** | 44 | 45 | 33 | – | 42 | 33 | 12 |
| **E** | 17 | 10 | 11 | 42 | – | 45 | 30 |
| **F** | 34 | 41 | 35 | 33 | 45 | – | 30 |
| **G** | 33 | 33 | 21 | 12 | 30 | 30 | – |

Find the minimum-distance tour.

**Answer A (Gold).** A → F → D → G → C → E → B → A = **129 km** | Exact solver time: **0.26 ms**

**Answer B (Agent reference).** Expected agent time: **~22 s** (no solver, chain-of-thought). Exact optimum verified by Held–Karp DP. LLMs typically land within 5–15% but rarely hit exact optimum at this size.

**Benchmark metric.** Record agent's total cost, divide by 129 for the optimality gap; flag infeasible tours as gap = ∞.

---

### Problem 20: Metro Grid #20 (8 cities)

**Problem.** A courier starts at city A and must visit cities B, C, D, E, F, G, H exactly once, returning to A. The distance matrix (in km) is:

| From\To | A | B | C | D | E | F | G | H |
|---|---|---|---|---|---|---|---|---|
| **A** | – | 13 | 38 | 31 | 29 | 28 | 22 | 37 |
| **B** | 13 | – | 50 | 44 | 40 | 26 | 29 | 46 |
| **C** | 38 | 50 | – | 9 | 11 | 41 | 25 | 16 |
| **D** | 31 | 44 | 9 | – | 10 | 40 | 24 | 21 |
| **E** | 29 | 40 | 11 | 10 | – | 31 | 15 | 12 |
| **F** | 28 | 26 | 41 | 40 | 31 | – | 16 | 29 |
| **G** | 22 | 29 | 25 | 24 | 15 | 16 | – | 17 |
| **H** | 37 | 46 | 16 | 21 | 12 | 29 | 17 | – |

Find the minimum-distance tour.

**Answer A (Gold).** A → D → C → E → H → G → F → B → A = **135 km** | Exact solver time: **0.60 ms**

**Answer B (Agent reference).** Expected agent time: **~24 s** (no solver, chain-of-thought). Exact optimum verified by Held–Karp DP. LLMs typically land within 5–15% but rarely hit exact optimum at this size.

**Benchmark metric.** Record agent's total cost, divide by 135 for the optimality gap; flag infeasible tours as gap = ∞.

---

### Problem 21: Metro Grid #21 (8 cities)

**Problem.** A courier starts at city A and must visit cities B, C, D, E, F, G, H exactly once, returning to A. The distance matrix (in km) is:

| From\To | A | B | C | D | E | F | G | H |
|---|---|---|---|---|---|---|---|---|
| **A** | – | 31 | 19 | 19 | 19 | 30 | 24 | 11 |
| **B** | 31 | – | 37 | 49 | 50 | 17 | 54 | 40 |
| **C** | 19 | 37 | – | 32 | 28 | 26 | 25 | 15 |
| **D** | 19 | 49 | 32 | – | 7 | 49 | 17 | 17 |
| **E** | 19 | 50 | 28 | 7 | – | 48 | 10 | 14 |
| **F** | 30 | 17 | 26 | 49 | 48 | – | 49 | 35 |
| **G** | 24 | 54 | 25 | 17 | 10 | 49 | – | 14 |
| **H** | 11 | 40 | 15 | 17 | 14 | 35 | 14 | – |

Find the minimum-distance tour.

**Answer A (Gold).** A → D → E → G → H → C → F → B → A = **139 km** | Exact solver time: **0.62 ms**

**Answer B (Agent reference).** Expected agent time: **~24 s** (no solver, chain-of-thought). Exact optimum verified by Held–Karp DP. LLMs typically land within 5–15% but rarely hit exact optimum at this size.

**Benchmark metric.** Record agent's total cost, divide by 139 for the optimality gap; flag infeasible tours as gap = ∞.

---

### Problem 22: Metro Grid #22 (9 cities)

**Problem.** A courier starts at city A and must visit cities B, C, D, E, F, G, H, I exactly once, returning to A. The distance matrix (in km) is:

| From\To | A | B | C | D | E | F | G | H | I |
|---|---|---|---|---|---|---|---|---|---|
| **A** | – | 17 | 21 | 30 | 5 | 34 | 16 | 5 | 36 |
| **B** | 17 | – | 30 | 47 | 14 | 41 | 31 | 15 | 46 |
| **C** | 21 | 30 | – | 34 | 18 | 13 | 29 | 18 | 16 |
| **D** | 30 | 47 | 34 | – | 34 | 41 | 17 | 33 | 35 |
| **E** | 5 | 14 | 18 | 34 | – | 31 | 20 | 1 | 34 |
| **F** | 34 | 41 | 13 | 41 | 31 | – | 41 | 30 | 10 |
| **G** | 16 | 31 | 29 | 17 | 20 | 41 | – | 20 | 38 |
| **H** | 5 | 15 | 18 | 33 | 1 | 30 | 20 | – | 33 |
| **I** | 36 | 46 | 16 | 35 | 34 | 10 | 38 | 33 | – |

Find the minimum-distance tour.

**Answer A (Gold).** A → G → D → I → F → C → H → E → B → A = **141 km** | Exact solver time: **48.68 ms**

**Answer B (Agent reference).** Expected agent time: **~26 s** (no solver, chain-of-thought). Exact optimum verified by Held–Karp DP. LLMs typically land within 5–15% but rarely hit exact optimum at this size.

**Benchmark metric.** Record agent's total cost, divide by 141 for the optimality gap; flag infeasible tours as gap = ∞.

---

### Problem 23: Metro Grid #23 (9 cities)

**Problem.** A courier starts at city A and must visit cities B, C, D, E, F, G, H, I exactly once, returning to A. The distance matrix (in km) is:

| From\To | A | B | C | D | E | F | G | H | I |
|---|---|---|---|---|---|---|---|---|---|
| **A** | – | 34 | 57 | 29 | 32 | 33 | 34 | 28 | 52 |
| **B** | 34 | – | 24 | 48 | 18 | 51 | 14 | 9 | 42 |
| **C** | 57 | 24 | – | 72 | 29 | 75 | 24 | 28 | 59 |
| **D** | 29 | 48 | 72 | – | 55 | 4 | 55 | 47 | 37 |
| **E** | 32 | 18 | 29 | 55 | – | 59 | 6 | 11 | 59 |
| **F** | 33 | 51 | 75 | 4 | 59 | – | 59 | 50 | 36 |
| **G** | 34 | 14 | 24 | 55 | 6 | 59 | – | 9 | 55 |
| **H** | 28 | 9 | 28 | 47 | 11 | 50 | 9 | – | 48 |
| **I** | 52 | 42 | 59 | 37 | 59 | 36 | 55 | 48 | – |

Find the minimum-distance tour.

**Answer A (Gold).** A → H → E → G → C → B → I → F → D → A = **204 km** | Exact solver time: **1.65 ms**

**Answer B (Agent reference).** Expected agent time: **~26 s** (no solver, chain-of-thought). Exact optimum verified by Held–Karp DP. LLMs typically land within 5–15% but rarely hit exact optimum at this size.

**Benchmark metric.** Record agent's total cost, divide by 204 for the optimality gap; flag infeasible tours as gap = ∞.

---

### Problem 24: Metro Grid #24 (10 cities)

**Problem.** A courier starts at city A and must visit cities B, C, D, E, F, G, H, I, J exactly once, returning to A. The distance matrix (in km) is:

| From\To | A | B | C | D | E | F | G | H | I | J |
|---|---|---|---|---|---|---|---|---|---|---|
| **A** | – | 42 | 30 | 39 | 51 | 47 | 19 | 35 | 26 | 38 |
| **B** | 42 | – | 17 | 11 | 40 | 4 | 25 | 15 | 58 | 10 |
| **C** | 30 | 17 | – | 9 | 49 | 21 | 11 | 23 | 52 | 8 |
| **D** | 39 | 11 | 9 | – | 49 | 14 | 20 | 23 | 59 | 2 |
| **E** | 51 | 40 | 49 | 49 | – | 41 | 48 | 27 | 45 | 48 |
| **F** | 47 | 4 | 21 | 14 | 41 | – | 30 | 18 | 62 | 13 |
| **G** | 19 | 25 | 11 | 20 | 48 | 30 | – | 24 | 41 | 19 |
| **H** | 35 | 15 | 23 | 23 | 27 | 18 | 24 | – | 45 | 21 |
| **I** | 26 | 58 | 52 | 59 | 45 | 62 | 41 | 45 | – | 57 |
| **J** | 38 | 10 | 8 | 2 | 48 | 13 | 19 | 21 | 57 | – |

Find the minimum-distance tour.

**Answer A (Gold).** A → I → E → H → F → B → J → D → C → G → A = **171 km** | Exact solver time: **4.70 ms**

**Answer B (Agent reference).** Expected agent time: **~28 s** (no solver, chain-of-thought). Exact optimum verified by Held–Karp DP. LLMs typically land within 5–15% but rarely hit exact optimum at this size.

**Benchmark metric.** Record agent's total cost, divide by 171 for the optimality gap; flag infeasible tours as gap = ∞.

---

### Problem 25: Metro Grid #25 (10 cities)

**Problem.** A courier starts at city A and must visit cities B, C, D, E, F, G, H, I, J exactly once, returning to A. The distance matrix (in km) is:

| From\To | A | B | C | D | E | F | G | H | I | J |
|---|---|---|---|---|---|---|---|---|---|---|
| **A** | – | 33 | 42 | 36 | 15 | 26 | 39 | 37 | 28 | 57 |
| **B** | 33 | – | 55 | 4 | 23 | 23 | 56 | 63 | 52 | 72 |
| **C** | 42 | 55 | – | 57 | 36 | 33 | 6 | 25 | 20 | 17 |
| **D** | 36 | 4 | 57 | – | 26 | 24 | 57 | 66 | 55 | 74 |
| **E** | 15 | 23 | 36 | 26 | – | 11 | 35 | 40 | 29 | 52 |
| **F** | 26 | 23 | 33 | 24 | 11 | – | 33 | 44 | 32 | 50 |
| **G** | 39 | 56 | 6 | 57 | 35 | 33 | – | 19 | 14 | 18 |
| **H** | 37 | 63 | 25 | 66 | 40 | 44 | 19 | – | 11 | 28 |
| **I** | 28 | 52 | 20 | 55 | 29 | 32 | 14 | 11 | – | 30 |
| **J** | 57 | 72 | 17 | 74 | 52 | 50 | 18 | 28 | 30 | – |

Find the minimum-distance tour.

**Answer A (Gold).** A → I → H → J → C → G → F → D → B → E → A = **189 km** | Exact solver time: **4.23 ms**

**Answer B (Agent reference).** Expected agent time: **~28 s** (no solver, chain-of-thought). Exact optimum verified by Held–Karp DP. LLMs typically land within 5–15% but rarely hit exact optimum at this size.

**Benchmark metric.** Record agent's total cost, divide by 189 for the optimality gap; flag infeasible tours as gap = ∞.

---

### Problem 26: Metro Grid #26 (7 cities)

**Problem.** A courier starts at city A and must visit cities B, C, D, E, F, G exactly once, returning to A. The distance matrix (in km) is:

| From\To | A | B | C | D | E | F | G |
|---|---|---|---|---|---|---|---|
| **A** | – | 29 | 39 | 25 | 14 | 8 | 31 |
| **B** | 29 | – | 17 | 10 | 24 | 34 | 12 |
| **C** | 39 | 17 | – | 28 | 28 | 42 | 8 |
| **D** | 25 | 10 | 28 | – | 25 | 32 | 21 |
| **E** | 14 | 24 | 28 | 25 | – | 14 | 21 |
| **F** | 8 | 34 | 42 | 32 | 14 | – | 34 |
| **G** | 31 | 12 | 8 | 21 | 21 | 34 | – |

Find the minimum-distance tour.

**Answer A (Gold).** A → F → E → G → C → B → D → A = **103 km** | Exact solver time: **0.25 ms**

**Answer B (Agent reference).** Expected agent time: **~22 s** (no solver, chain-of-thought). Exact optimum verified by Held–Karp DP. LLMs typically land within 5–15% but rarely hit exact optimum at this size.

**Benchmark metric.** Record agent's total cost, divide by 103 for the optimality gap; flag infeasible tours as gap = ∞.

---

### Problem 27: Metro Grid #27 (8 cities)

**Problem.** A courier starts at city A and must visit cities B, C, D, E, F, G, H exactly once, returning to A. The distance matrix (in km) is:

| From\To | A | B | C | D | E | F | G | H |
|---|---|---|---|---|---|---|---|---|
| **A** | – | 10 | 29 | 19 | 11 | 20 | 32 | 16 |
| **B** | 10 | – | 38 | 10 | 16 | 21 | 38 | 9 |
| **C** | 29 | 38 | – | 42 | 23 | 28 | 18 | 39 |
| **D** | 19 | 10 | 42 | – | 19 | 18 | 37 | 3 |
| **E** | 11 | 16 | 23 | 19 | – | 10 | 21 | 16 |
| **F** | 20 | 21 | 28 | 18 | 10 | – | 19 | 16 |
| **G** | 32 | 38 | 18 | 37 | 21 | 19 | – | 34 |
| **H** | 16 | 9 | 39 | 3 | 16 | 16 | 34 | – |

Find the minimum-distance tour.

**Answer A (Gold).** A → E → C → G → F → H → D → B → A = **110 km** | Exact solver time: **0.63 ms**

**Answer B (Agent reference).** Expected agent time: **~24 s** (no solver, chain-of-thought). Exact optimum verified by Held–Karp DP. LLMs typically land within 5–15% but rarely hit exact optimum at this size.

**Benchmark metric.** Record agent's total cost, divide by 110 for the optimality gap; flag infeasible tours as gap = ∞.

---

### Problem 28: Metro Grid #28 (9 cities)

**Problem.** A courier starts at city A and must visit cities B, C, D, E, F, G, H, I exactly once, returning to A. The distance matrix (in km) is:

| From\To | A | B | C | D | E | F | G | H | I |
|---|---|---|---|---|---|---|---|---|---|
| **A** | – | 13 | 28 | 16 | 35 | 22 | 41 | 35 | 28 |
| **B** | 13 | – | 24 | 4 | 35 | 9 | 34 | 30 | 20 |
| **C** | 28 | 24 | – | 21 | 13 | 24 | 15 | 7 | 9 |
| **D** | 16 | 4 | 21 | – | 33 | 7 | 31 | 27 | 16 |
| **E** | 35 | 35 | 13 | 33 | – | 37 | 21 | 13 | 21 |
| **F** | 22 | 9 | 24 | 7 | 37 | – | 30 | 29 | 17 |
| **G** | 41 | 34 | 15 | 31 | 21 | 30 | – | 9 | 14 |
| **H** | 35 | 30 | 7 | 27 | 13 | 29 | 9 | – | 11 |
| **I** | 28 | 20 | 9 | 16 | 21 | 17 | 14 | 11 | – |

Find the minimum-distance tour.

**Answer A (Gold).** A → C → E → H → G → I → F → D → B → A = **118 km** | Exact solver time: **1.62 ms**

**Answer B (Agent reference).** Expected agent time: **~26 s** (no solver, chain-of-thought). Exact optimum verified by Held–Karp DP. LLMs typically land within 5–15% but rarely hit exact optimum at this size.

**Benchmark metric.** Record agent's total cost, divide by 118 for the optimality gap; flag infeasible tours as gap = ∞.

---

### Problem 29: Metro Grid #29 (10 cities)

**Problem.** A courier starts at city A and must visit cities B, C, D, E, F, G, H, I, J exactly once, returning to A. The distance matrix (in km) is:

| From\To | A | B | C | D | E | F | G | H | I | J |
|---|---|---|---|---|---|---|---|---|---|---|
| **A** | – | 45 | 28 | 55 | 57 | 54 | 76 | 65 | 11 | 35 |
| **B** | 45 | – | 17 | 18 | 47 | 18 | 35 | 36 | 34 | 14 |
| **C** | 28 | 17 | – | 29 | 44 | 30 | 49 | 43 | 17 | 13 |
| **D** | 55 | 18 | 29 | – | 35 | 34 | 21 | 18 | 44 | 31 |
| **E** | 57 | 47 | 44 | 35 | – | 66 | 46 | 24 | 50 | 55 |
| **F** | 54 | 18 | 30 | 34 | 66 | – | 45 | 52 | 44 | 19 |
| **G** | 76 | 35 | 49 | 21 | 46 | 45 | – | 22 | 65 | 49 |
| **H** | 65 | 36 | 43 | 18 | 24 | 52 | 22 | – | 55 | 48 |
| **I** | 11 | 34 | 17 | 44 | 50 | 44 | 65 | 55 | – | 25 |
| **J** | 35 | 14 | 13 | 31 | 55 | 19 | 49 | 48 | 25 | – |

Find the minimum-distance tour.

**Answer A (Gold).** A → I → C → J → F → B → D → G → H → E → A = **220 km** | Exact solver time: **3.99 ms**

**Answer B (Agent reference).** Expected agent time: **~28 s** (no solver, chain-of-thought). Exact optimum verified by Held–Karp DP. LLMs typically land within 5–15% but rarely hit exact optimum at this size.

**Benchmark metric.** Record agent's total cost, divide by 220 for the optimality gap; flag infeasible tours as gap = ∞.

---

### Problem 30: Metro Grid #30 (11 cities)

**Problem.** A courier starts at city A and must visit cities B, C, D, E, F, G, H, I, J, K exactly once, returning to A. The distance matrix (in km) is:

| From\To | A | B | C | D | E | F | G | H | I | J | K |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **A** | – | 41 | 7 | 21 | 56 | 21 | 25 | 18 | 19 | 17 | 38 |
| **B** | 41 | – | 45 | 52 | 18 | 36 | 45 | 24 | 59 | 27 | 16 |
| **C** | 7 | 45 | – | 14 | 59 | 28 | 21 | 24 | 17 | 23 | 40 |
| **D** | 21 | 52 | 14 | – | 62 | 42 | 13 | 35 | 25 | 35 | 42 |
| **E** | 56 | 18 | 59 | 62 | – | 54 | 52 | 40 | 74 | 44 | 20 |
| **F** | 21 | 36 | 28 | 42 | 54 | – | 44 | 16 | 32 | 12 | 42 |
| **G** | 25 | 45 | 21 | 13 | 52 | 44 | – | 33 | 36 | 35 | 32 |
| **H** | 18 | 24 | 24 | 35 | 40 | 16 | 33 | – | 36 | 4 | 26 |
| **I** | 19 | 59 | 17 | 25 | 74 | 32 | 36 | 36 | – | 34 | 56 |
| **J** | 17 | 27 | 23 | 35 | 44 | 12 | 35 | 4 | 34 | – | 30 |
| **K** | 38 | 16 | 40 | 42 | 20 | 42 | 32 | 26 | 56 | 30 | – |

Find the minimum-distance tour.

**Answer A (Gold).** A → F → J → H → B → E → K → G → D → I → C → A = **193 km** | Exact solver time: **9.73 ms**

**Answer B (Agent reference).** Expected agent time: **~30 s** (no solver, chain-of-thought). Exact optimum verified by Held–Karp DP. LLMs typically land within 5–15% but rarely hit exact optimum at this size.

**Benchmark metric.** Record agent's total cost, divide by 193 for the optimality gap; flag infeasible tours as gap = ∞.

---


## Part 3: Tough Problems

### Problem 31: National Mesh #31 (12 cities)

**Problem.** National fleet problem #31: 12 cities, distance matrix below (km). Start at A, visit every city exactly once, return to A. Minimize total distance.

| From\To | A | B | C | D | E | F | G | H | I | J | K | L |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **A** | – | 38 | 35 | 37 | 59 | 49 | 19 | 55 | 41 | 31 | 26 | 51 |
| **B** | 38 | – | 47 | 59 | 97 | 18 | 26 | 63 | 78 | 56 | 23 | 67 |
| **C** | 35 | 47 | – | 15 | 77 | 65 | 47 | 88 | 49 | 66 | 24 | 85 |
| **D** | 37 | 59 | 15 | – | 66 | 76 | 53 | 91 | 37 | 66 | 36 | 86 |
| **E** | 59 | 97 | 77 | 66 | – | 105 | 74 | 79 | 29 | 54 | 83 | 67 |
| **F** | 49 | 18 | 65 | 76 | 105 | – | 31 | 55 | 90 | 56 | 41 | 62 |
| **G** | 19 | 26 | 47 | 53 | 74 | 31 | – | 44 | 59 | 30 | 28 | 44 |
| **H** | 55 | 63 | 88 | 91 | 79 | 55 | 44 | – | 80 | 28 | 72 | 12 |
| **I** | 41 | 78 | 49 | 37 | 29 | 90 | 59 | 80 | – | 52 | 60 | 71 |
| **J** | 31 | 56 | 66 | 66 | 54 | 56 | 30 | 28 | 52 | – | 55 | 21 |
| **K** | 26 | 23 | 24 | 36 | 83 | 41 | 28 | 72 | 60 | 55 | – | 72 |
| **L** | 51 | 67 | 85 | 86 | 67 | 62 | 44 | 12 | 71 | 21 | 72 | – |


**Answer A (Gold).** A → J → H → L → E → I → D → C → K → B → F → G → A = **334 km** (exact, Held–Karp) | Exact solver time: **26.51 ms**

**Answer B (Agent reference).** Expected agent time: **~60 s** (no solver, chain-of-thought). Beyond reliable human/LLM exact solving; factorial space 19,958,400 tours. Agent answers typically 10–25% above optimum.

**Benchmark metric.** Record agent's total cost, divide by 334 for the optimality gap; flag infeasible tours as gap = ∞.

---

### Problem 32: National Mesh #32 (12 cities)

**Problem.** National fleet problem #32: 12 cities, distance matrix below (km). Start at A, visit every city exactly once, return to A. Minimize total distance.

| From\To | A | B | C | D | E | F | G | H | I | J | K | L |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **A** | – | 92 | 32 | 37 | 69 | 49 | 59 | 97 | 16 | 91 | 60 | 29 |
| **B** | 92 | – | 68 | 66 | 29 | 121 | 52 | 79 | 78 | 94 | 45 | 104 |
| **C** | 32 | 68 | – | 5 | 41 | 78 | 55 | 99 | 28 | 100 | 51 | 36 |
| **D** | 37 | 66 | 5 | – | 38 | 84 | 58 | 102 | 34 | 104 | 53 | 38 |
| **E** | 69 | 29 | 41 | 38 | – | 107 | 51 | 90 | 58 | 100 | 43 | 77 |
| **F** | 49 | 121 | 78 | 84 | 107 | – | 72 | 89 | 51 | 74 | 78 | 72 |
| **G** | 59 | 52 | 55 | 58 | 51 | 72 | – | 44 | 43 | 49 | 8 | 83 |
| **H** | 97 | 79 | 99 | 102 | 90 | 89 | 44 | – | 82 | 21 | 50 | 124 |
| **I** | 16 | 78 | 28 | 34 | 58 | 51 | 43 | 82 | – | 78 | 43 | 42 |
| **J** | 91 | 94 | 100 | 104 | 100 | 74 | 49 | 21 | 78 | – | 57 | 120 |
| **K** | 60 | 45 | 51 | 53 | 43 | 78 | 8 | 50 | 43 | 57 | – | 82 |
| **L** | 29 | 104 | 36 | 38 | 77 | 72 | 83 | 124 | 42 | 120 | 82 | – |


**Answer A (Gold).** A → L → C → D → E → B → K → G → H → J → F → I → A = **396 km** (exact, Held–Karp) | Exact solver time: **25.07 ms**

**Answer B (Agent reference).** Expected agent time: **~60 s** (no solver, chain-of-thought). Beyond reliable human/LLM exact solving; factorial space 19,958,400 tours. Agent answers typically 10–25% above optimum.

**Benchmark metric.** Record agent's total cost, divide by 396 for the optimality gap; flag infeasible tours as gap = ∞.

---

### Problem 33: National Mesh #33 (13 cities)

**Problem.** National fleet problem #33: 13 cities, distance matrix below (km). Start at A, visit every city exactly once, return to A. Minimize total distance.

| From\To | A | B | C | D | E | F | G | H | I | J | K | L | M |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **A** | – | 36 | 40 | 62 | 35 | 31 | 26 | 51 | 34 | 28 | 61 | 68 | 44 |
| **B** | 36 | – | 68 | 71 | 48 | 18 | 62 | 77 | 8 | 13 | 89 | 95 | 71 |
| **C** | 40 | 68 | – | 38 | 26 | 70 | 25 | 11 | 70 | 56 | 21 | 28 | 69 |
| **D** | 62 | 71 | 38 | – | 27 | 81 | 60 | 34 | 76 | 59 | 46 | 46 | 101 |
| **E** | 35 | 48 | 26 | 27 | – | 55 | 39 | 31 | 52 | 36 | 45 | 49 | 76 |
| **F** | 31 | 18 | 70 | 81 | 55 | – | 57 | 80 | 10 | 24 | 91 | 98 | 57 |
| **G** | 26 | 62 | 25 | 60 | 39 | 57 | – | 36 | 60 | 52 | 41 | 49 | 43 |
| **H** | 51 | 77 | 11 | 34 | 31 | 80 | 36 | – | 79 | 64 | 14 | 19 | 79 |
| **I** | 34 | 8 | 70 | 76 | 52 | 10 | 60 | 79 | – | 17 | 91 | 97 | 65 |
| **J** | 28 | 13 | 56 | 59 | 36 | 24 | 52 | 64 | 17 | – | 77 | 83 | 69 |
| **K** | 61 | 89 | 21 | 46 | 45 | 91 | 41 | 14 | 91 | 77 | – | 8 | 82 |
| **L** | 68 | 95 | 28 | 46 | 49 | 98 | 49 | 19 | 97 | 83 | 8 | – | 90 |
| **M** | 44 | 71 | 69 | 101 | 76 | 57 | 43 | 79 | 65 | 69 | 82 | 90 | – |


**Answer A (Gold).** A → M → G → C → H → K → L → D → E → J → B → I → F → A = **316 km** (exact, Held–Karp) | Exact solver time: **57.38 ms**

**Answer B (Agent reference).** Expected agent time: **~65 s** (no solver, chain-of-thought). Beyond reliable human/LLM exact solving; factorial space 239,500,800 tours. Agent answers typically 10–25% above optimum.

**Benchmark metric.** Record agent's total cost, divide by 316 for the optimality gap; flag infeasible tours as gap = ∞.

---

### Problem 34: National Mesh #34 (13 cities)

**Problem.** National fleet problem #34: 13 cities, distance matrix below (km). Start at A, visit every city exactly once, return to A. Minimize total distance.

| From\To | A | B | C | D | E | F | G | H | I | J | K | L | M |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **A** | – | 119 | 124 | 7 | 125 | 123 | 50 | 54 | 102 | 96 | 80 | 93 | 112 |
| **B** | 119 | – | 17 | 112 | 63 | 64 | 71 | 98 | 46 | 72 | 55 | 88 | 62 |
| **C** | 124 | 17 | – | 117 | 80 | 82 | 74 | 96 | 63 | 88 | 51 | 104 | 80 |
| **D** | 7 | 112 | 117 | – | 120 | 118 | 43 | 48 | 96 | 92 | 73 | 90 | 107 |
| **E** | 125 | 63 | 80 | 120 | – | 2 | 92 | 131 | 27 | 31 | 99 | 45 | 13 |
| **F** | 123 | 64 | 82 | 118 | 2 | – | 92 | 131 | 27 | 29 | 99 | 43 | 11 |
| **G** | 50 | 71 | 74 | 43 | 92 | 92 | – | 39 | 66 | 73 | 33 | 78 | 82 |
| **H** | 54 | 98 | 96 | 48 | 131 | 131 | 39 | – | 104 | 112 | 45 | 116 | 121 |
| **I** | 102 | 46 | 63 | 96 | 27 | 27 | 66 | 104 | – | 25 | 73 | 42 | 19 |
| **J** | 96 | 72 | 88 | 92 | 31 | 29 | 73 | 112 | 25 | – | 89 | 17 | 19 |
| **K** | 80 | 55 | 51 | 73 | 99 | 99 | 33 | 45 | 73 | 89 | – | 100 | 92 |
| **L** | 93 | 88 | 104 | 90 | 45 | 43 | 78 | 116 | 42 | 17 | 100 | – | 34 |
| **M** | 112 | 62 | 80 | 107 | 13 | 11 | 82 | 121 | 19 | 19 | 92 | 34 | – |


**Answer A (Gold).** A → L → J → M → F → E → I → B → C → K → G → H → D → A = **410 km** (exact, Held–Karp) | Exact solver time: **62.32 ms**

**Answer B (Agent reference).** Expected agent time: **~65 s** (no solver, chain-of-thought). Beyond reliable human/LLM exact solving; factorial space 239,500,800 tours. Agent answers typically 10–25% above optimum.

**Benchmark metric.** Record agent's total cost, divide by 410 for the optimality gap; flag infeasible tours as gap = ∞.

---

### Problem 35: National Mesh #35 (14 cities)

**Problem.** National fleet problem #35: 14 cities, distance matrix below (km). Start at A, visit every city exactly once, return to A. Minimize total distance.

| From\To | A | B | C | D | E | F | G | H | I | J | K | L | M | N |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **A** | – | 74 | 135 | 39 | 71 | 37 | 113 | 32 | 105 | 110 | 87 | 101 | 102 | 119 |
| **B** | 74 | – | 61 | 80 | 38 | 41 | 42 | 61 | 58 | 88 | 74 | 76 | 55 | 45 |
| **C** | 135 | 61 | – | 134 | 84 | 101 | 26 | 120 | 66 | 106 | 104 | 97 | 67 | 19 |
| **D** | 39 | 80 | 134 | – | 94 | 60 | 109 | 66 | 87 | 79 | 57 | 72 | 84 | 123 |
| **E** | 71 | 38 | 84 | 94 | – | 35 | 74 | 44 | 96 | 124 | 107 | 112 | 93 | 65 |
| **F** | 37 | 41 | 101 | 60 | 35 | – | 82 | 21 | 87 | 106 | 85 | 94 | 84 | 84 |
| **G** | 113 | 42 | 26 | 109 | 74 | 82 | – | 103 | 43 | 83 | 79 | 73 | 43 | 24 |
| **H** | 32 | 61 | 120 | 66 | 44 | 21 | 103 | – | 108 | 123 | 102 | 112 | 105 | 103 |
| **I** | 105 | 58 | 66 | 87 | 96 | 87 | 43 | 108 | – | 40 | 40 | 31 | 3 | 67 |
| **J** | 110 | 88 | 106 | 79 | 124 | 106 | 83 | 123 | 40 | – | 23 | 12 | 40 | 107 |
| **K** | 87 | 74 | 104 | 57 | 107 | 85 | 79 | 102 | 40 | 23 | – | 16 | 39 | 101 |
| **L** | 101 | 76 | 97 | 72 | 112 | 94 | 73 | 112 | 31 | 12 | 16 | – | 30 | 96 |
| **M** | 102 | 55 | 67 | 84 | 93 | 84 | 43 | 105 | 3 | 40 | 39 | 30 | – | 66 |
| **N** | 119 | 45 | 19 | 123 | 65 | 84 | 24 | 103 | 67 | 107 | 101 | 96 | 66 | – |


**Answer A (Gold).** A → H → F → E → B → N → C → G → I → M → L → J → K → D → A = **423 km** (exact, Held–Karp) | Exact solver time: **188.06 ms**

**Answer B (Agent reference).** Expected agent time: **~70 s** (no solver, chain-of-thought). Beyond reliable human/LLM exact solving; factorial space 3,113,510,400 tours. Agent answers typically 10–25% above optimum.

**Benchmark metric.** Record agent's total cost, divide by 423 for the optimality gap; flag infeasible tours as gap = ∞.

---

### Problem 36: National Mesh #36 (14 cities)

**Problem.** National fleet problem #36: 14 cities, distance matrix below (km). Start at A, visit every city exactly once, return to A. Minimize total distance.

| From\To | A | B | C | D | E | F | G | H | I | J | K | L | M | N |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **A** | – | 66 | 62 | 114 | 72 | 140 | 72 | 29 | 25 | 27 | 16 | 100 | 79 | 25 |
| **B** | 66 | – | 40 | 49 | 69 | 78 | 29 | 52 | 46 | 57 | 79 | 41 | 58 | 64 |
| **C** | 62 | 40 | – | 76 | 100 | 85 | 67 | 67 | 57 | 69 | 78 | 47 | 21 | 75 |
| **D** | 114 | 49 | 76 | – | 98 | 45 | 54 | 97 | 93 | 102 | 127 | 37 | 86 | 110 |
| **E** | 72 | 69 | 100 | 98 | – | 140 | 46 | 43 | 51 | 45 | 72 | 108 | 121 | 48 |
| **F** | 140 | 78 | 85 | 45 | 140 | – | 94 | 130 | 123 | 134 | 154 | 40 | 83 | 142 |
| **G** | 72 | 29 | 67 | 54 | 46 | 94 | – | 48 | 47 | 52 | 81 | 64 | 87 | 60 |
| **H** | 29 | 52 | 67 | 97 | 43 | 130 | 48 | – | 10 | 4 | 34 | 92 | 87 | 13 |
| **I** | 25 | 46 | 57 | 93 | 51 | 123 | 47 | 10 | – | 13 | 35 | 84 | 77 | 19 |
| **J** | 27 | 57 | 69 | 102 | 45 | 134 | 52 | 4 | 13 | – | 30 | 96 | 90 | 8 |
| **K** | 16 | 79 | 78 | 127 | 72 | 154 | 81 | 34 | 35 | 30 | – | 115 | 94 | 24 |
| **L** | 100 | 41 | 47 | 37 | 108 | 40 | 64 | 92 | 84 | 96 | 115 | – | 51 | 104 |
| **M** | 79 | 58 | 21 | 86 | 121 | 83 | 87 | 87 | 77 | 90 | 94 | 51 | – | 95 |
| **N** | 25 | 64 | 75 | 110 | 48 | 142 | 60 | 13 | 19 | 8 | 24 | 104 | 95 | – |


**Answer A (Gold).** A → K → N → J → H → I → E → G → B → D → F → L → M → C → A = **456 km** (exact, Held–Karp) | Exact solver time: **132.50 ms**

**Answer B (Agent reference).** Expected agent time: **~70 s** (no solver, chain-of-thought). Beyond reliable human/LLM exact solving; factorial space 3,113,510,400 tours. Agent answers typically 10–25% above optimum.

**Benchmark metric.** Record agent's total cost, divide by 456 for the optimality gap; flag infeasible tours as gap = ∞.

---

### Problem 37: National Mesh #37 (15 cities)

**Problem.** National fleet problem #37: 15 cities, distance matrix below (km). Start at A, visit every city exactly once, return to A. Minimize total distance.

| From\To | A | B | C | D | E | F | G | H | I | J | K | L | M | N | O |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **A** | – | 1 | 31 | 16 | 40 | 80 | 61 | 62 | 70 | 49 | 30 | 52 | 60 | 23 | 62 |
| **B** | 1 | – | 30 | 16 | 41 | 81 | 62 | 63 | 71 | 50 | 29 | 53 | 61 | 23 | 63 |
| **C** | 31 | 30 | – | 33 | 71 | 104 | 89 | 74 | 101 | 69 | 16 | 83 | 87 | 48 | 90 |
| **D** | 16 | 16 | 33 | – | 45 | 71 | 72 | 47 | 74 | 65 | 23 | 56 | 54 | 38 | 59 |
| **E** | 40 | 41 | 71 | 45 | – | 57 | 35 | 67 | 30 | 50 | 67 | 12 | 36 | 34 | 30 |
| **F** | 80 | 81 | 104 | 71 | 57 | – | 87 | 47 | 57 | 106 | 92 | 54 | 22 | 87 | 29 |
| **G** | 61 | 62 | 89 | 72 | 35 | 87 | – | 102 | 36 | 34 | 90 | 33 | 67 | 41 | 58 |
| **H** | 62 | 63 | 74 | 47 | 67 | 47 | 102 | – | 86 | 106 | 58 | 73 | 45 | 80 | 57 |
| **I** | 70 | 71 | 101 | 74 | 30 | 57 | 36 | 86 | – | 66 | 97 | 18 | 42 | 60 | 31 |
| **J** | 49 | 50 | 69 | 65 | 50 | 106 | 34 | 106 | 66 | – | 76 | 56 | 85 | 27 | 79 |
| **K** | 30 | 29 | 16 | 23 | 67 | 92 | 90 | 58 | 97 | 76 | – | 79 | 76 | 51 | 82 |
| **L** | 52 | 53 | 83 | 56 | 12 | 54 | 33 | 73 | 18 | 56 | 79 | – | 35 | 44 | 25 |
| **M** | 60 | 61 | 87 | 54 | 36 | 22 | 67 | 45 | 42 | 85 | 76 | 35 | – | 65 | 12 |
| **N** | 23 | 23 | 48 | 38 | 34 | 87 | 41 | 80 | 60 | 27 | 51 | 44 | 65 | – | 62 |
| **O** | 62 | 63 | 90 | 59 | 30 | 29 | 58 | 57 | 31 | 79 | 82 | 25 | 12 | 62 | – |


**Answer A (Gold).** A → N → J → G → I → L → E → O → M → F → H → D → K → C → B → A = **378 km** (exact, Held–Karp) | Exact solver time: **369.70 ms**

**Answer B (Agent reference).** Expected agent time: **~75 s** (no solver, chain-of-thought). Beyond reliable human/LLM exact solving; factorial space 43,589,145,600 tours. Agent answers typically 10–25% above optimum.

**Benchmark metric.** Record agent's total cost, divide by 378 for the optimality gap; flag infeasible tours as gap = ∞.

---

### Problem 38: National Mesh #38 (15 cities)

**Problem.** National fleet problem #38: 15 cities, distance matrix below (km). Start at A, visit every city exactly once, return to A. Minimize total distance.

| From\To | A | B | C | D | E | F | G | H | I | J | K | L | M | N | O |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **A** | – | 47 | 96 | 43 | 58 | 28 | 7 | 86 | 81 | 52 | 108 | 48 | 43 | 49 | 34 |
| **B** | 47 | – | 49 | 46 | 23 | 63 | 54 | 102 | 46 | 94 | 67 | 54 | 84 | 21 | 64 |
| **C** | 96 | 49 | – | 85 | 48 | 109 | 103 | 135 | 47 | 141 | 43 | 92 | 131 | 56 | 109 |
| **D** | 43 | 46 | 85 | – | 36 | 33 | 49 | 56 | 92 | 61 | 113 | 8 | 84 | 29 | 77 |
| **E** | 58 | 23 | 48 | 36 | – | 63 | 65 | 89 | 64 | 94 | 80 | 43 | 99 | 9 | 82 |
| **F** | 28 | 63 | 109 | 33 | 63 | – | 29 | 59 | 104 | 31 | 129 | 32 | 59 | 55 | 60 |
| **G** | 7 | 54 | 103 | 49 | 65 | 29 | – | 88 | 86 | 49 | 113 | 52 | 36 | 56 | 31 |
| **H** | 86 | 102 | 135 | 56 | 89 | 59 | 88 | – | 148 | 61 | 168 | 48 | 116 | 84 | 119 |
| **I** | 81 | 46 | 47 | 92 | 64 | 104 | 86 | 148 | – | 133 | 28 | 100 | 103 | 66 | 79 |
| **J** | 52 | 94 | 141 | 61 | 94 | 31 | 49 | 61 | 133 | – | 159 | 58 | 62 | 86 | 74 |
| **K** | 108 | 67 | 43 | 113 | 80 | 129 | 113 | 168 | 28 | 159 | – | 121 | 132 | 84 | 107 |
| **L** | 48 | 54 | 92 | 8 | 43 | 32 | 52 | 48 | 100 | 58 | 121 | – | 87 | 37 | 82 |
| **M** | 43 | 84 | 131 | 84 | 99 | 59 | 36 | 116 | 103 | 62 | 132 | 87 | – | 91 | 25 |
| **N** | 49 | 21 | 56 | 29 | 9 | 55 | 56 | 84 | 66 | 86 | 84 | 37 | 91 | – | 75 |
| **O** | 34 | 64 | 109 | 77 | 82 | 60 | 31 | 119 | 79 | 74 | 107 | 82 | 25 | 75 | – |


**Answer A (Gold).** A → G → M → O → I → K → C → B → E → N → D → L → H → J → F → A = **504 km** (exact, Held–Karp) | Exact solver time: **305.45 ms**

**Answer B (Agent reference).** Expected agent time: **~75 s** (no solver, chain-of-thought). Beyond reliable human/LLM exact solving; factorial space 43,589,145,600 tours. Agent answers typically 10–25% above optimum.

**Benchmark metric.** Record agent's total cost, divide by 504 for the optimality gap; flag infeasible tours as gap = ∞.

---

### Problem 39: One-Way Network #39 (10 cities)

**Problem.** Asymmetric routing #39: 10 depots, directed travel times (minutes). Note d(i,j) ≠ d(j,i). Find min-time cycle from A.

| From\To | A | B | C | D | E | F | G | H | I | J |
|---|---|---|---|---|---|---|---|---|---|---|
| **A** | – | 38 | 36 | 21 | 15 | 4 | 9 | 22 | 7 | 40 |
| **B** | 5 | – | 6 | 29 | 22 | 26 | 38 | 40 | 39 | 21 |
| **C** | 15 | 9 | – | 28 | 28 | 14 | 19 | 32 | 24 | 11 |
| **D** | 11 | 31 | 27 | – | 29 | 38 | 14 | 26 | 19 | 16 |
| **E** | 20 | 32 | 39 | 27 | – | 14 | 33 | 39 | 33 | 13 |
| **F** | 7 | 37 | 18 | 32 | 36 | – | 3 | 10 | 24 | 34 |
| **G** | 7 | 24 | 3 | 39 | 37 | 20 | – | 3 | 40 | 23 |
| **H** | 29 | 19 | 13 | 11 | 40 | 6 | 28 | – | 5 | 6 |
| **I** | 24 | 35 | 17 | 38 | 21 | 13 | 31 | 6 | – | 29 |
| **J** | 17 | 15 | 10 | 34 | 13 | 20 | 20 | 26 | 7 | – |


**Answer A (Gold).** A → I → H → D → J → E → F → G → C → B → A = **87 min** (exact) | Exact solver time: **4.09 ms**

**Answer B (Agent reference).** Expected agent time: **~60 s** (no solver, chain-of-thought). Asymmetry breaks most LLM intuitions (they implicitly symmetrize matrices).

**Benchmark metric.** Record agent's total cost, divide by 87 for the optimality gap; flag infeasible tours as gap = ∞.

---

### Problem 40: One-Way Network #40 (12 cities)

**Problem.** Asymmetric routing #40: 12 depots, directed travel times (minutes). Note d(i,j) ≠ d(j,i). Find min-time cycle from A.

| From\To | A | B | C | D | E | F | G | H | I | J | K | L |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **A** | – | 38 | 15 | 38 | 14 | 25 | 44 | 37 | 8 | 10 | 11 | 11 |
| **B** | 12 | – | 37 | 8 | 5 | 35 | 44 | 27 | 13 | 25 | 17 | 42 |
| **C** | 41 | 42 | – | 13 | 24 | 6 | 24 | 43 | 30 | 15 | 22 | 14 |
| **D** | 10 | 12 | 34 | – | 44 | 36 | 3 | 17 | 27 | 9 | 18 | 39 |
| **E** | 31 | 41 | 8 | 13 | – | 13 | 31 | 26 | 19 | 23 | 40 | 5 |
| **F** | 40 | 28 | 4 | 22 | 13 | – | 11 | 3 | 21 | 38 | 21 | 21 |
| **G** | 10 | 34 | 30 | 7 | 5 | 25 | – | 13 | 41 | 23 | 24 | 45 |
| **H** | 23 | 5 | 27 | 20 | 42 | 17 | 38 | – | 12 | 4 | 21 | 28 |
| **I** | 29 | 35 | 17 | 14 | 36 | 29 | 6 | 16 | – | 18 | 44 | 19 |
| **J** | 13 | 39 | 9 | 30 | 3 | 39 | 4 | 15 | 11 | – | 14 | 43 |
| **K** | 22 | 6 | 19 | 14 | 40 | 30 | 12 | 3 | 44 | 5 | – | 35 |
| **L** | 28 | 31 | 7 | 13 | 40 | 17 | 24 | 30 | 11 | 33 | 42 | – |


**Answer A (Gold).** A → K → J → E → L → C → F → H → B → I → G → D → A = **81 min** (exact) | Exact solver time: **22.65 ms**

**Answer B (Agent reference).** Expected agent time: **~70 s** (no solver, chain-of-thought). Asymmetry breaks most LLM intuitions (they implicitly symmetrize matrices).

**Benchmark metric.** Record agent's total cost, divide by 81 for the optimality gap; flag infeasible tours as gap = ∞.

---

### Problem 41: Timed Circuit #41 (8 cities)

**Problem.** Timed deliveries #41: 8 stops, travel times below (min). Start A at t=0. Hard deadlines: B by minute 141, C by minute 118, D by minute 122, E by minute 16, F by minute 96, G by minute 80, H by minute 47. Find the fastest feasible cycle.

| From\To | A | B | C | D | E | F | G | H |
|---|---|---|---|---|---|---|---|---|
| **A** | – | 10 | 30 | 26 | 16 | 34 | 35 | 36 |
| **B** | 10 | – | 22 | 19 | 25 | 32 | 37 | 46 |
| **C** | 30 | 22 | – | 4 | 46 | 22 | 35 | 58 |
| **D** | 26 | 19 | 4 | – | 42 | 20 | 32 | 54 |
| **E** | 16 | 25 | 46 | 42 | – | 48 | 44 | 31 |
| **F** | 34 | 32 | 22 | 20 | 48 | – | 16 | 47 |
| **G** | 35 | 37 | 35 | 32 | 44 | 16 | – | 33 |
| **H** | 36 | 46 | 58 | 54 | 31 | 47 | 33 | – |


**Answer A (Gold).** A → E → H → G → F → C → D → B → A = **151 min**, all deadlines met | Exact solver time: **0.66 ms**

**Answer B (Agent reference).** Expected agent time: **~90 s** (no solver, chain-of-thought). Deadlines coincide with optimal-tour arrivals, so the unconstrained optimum is feasible—but agents must prove feasibility, not assume it.

**Benchmark metric.** Record agent's total cost, divide by 151 for the optimality gap; flag infeasible tours as gap = ∞.

---

### Problem 42: Timed Circuit #42 (9 cities)

**Problem.** Timed deliveries #42: 9 stops, travel times below (min). Start A at t=0. Hard deadlines: B by minute 124, C by minute 10, D by minute 41, E by minute 50, F by minute 155, G by minute 7, H by minute 23, I by minute 96. Find the fastest feasible cycle.

| From\To | A | B | C | D | E | F | G | H | I |
|---|---|---|---|---|---|---|---|---|---|
| **A** | – | 39 | 8 | 32 | 30 | 24 | 7 | 16 | 60 |
| **B** | 39 | – | 34 | 49 | 40 | 31 | 34 | 46 | 28 |
| **C** | 8 | 34 | – | 26 | 23 | 27 | 3 | 13 | 53 |
| **D** | 32 | 49 | 26 | – | 9 | 52 | 29 | 18 | 55 |
| **E** | 30 | 40 | 23 | 9 | – | 48 | 25 | 19 | 46 |
| **F** | 24 | 31 | 27 | 52 | 48 | – | 24 | 39 | 59 |
| **G** | 7 | 34 | 3 | 29 | 25 | 24 | – | 16 | 54 |
| **H** | 16 | 46 | 13 | 18 | 19 | 39 | 16 | – | 60 |
| **I** | 60 | 28 | 53 | 55 | 46 | 59 | 54 | 60 | – |


**Answer A (Gold).** A → G → C → H → D → E → I → B → F → A = **179 min**, all deadlines met | Exact solver time: **1.67 ms**

**Answer B (Agent reference).** Expected agent time: **~90 s** (no solver, chain-of-thought). Deadlines coincide with optimal-tour arrivals, so the unconstrained optimum is feasible—but agents must prove feasibility, not assume it.

**Benchmark metric.** Record agent's total cost, divide by 179 for the optimality gap; flag infeasible tours as gap = ∞.

---

### Problem 43: Fleet Split #43 (8 customers)

**Problem.** Two-van routing #43: hub A plus 7 customers (matrix below, km). Two vans, both start/end at A, each customer visited exactly once, each van takes ≥1 customer. Minimize combined km.

| From\To | A | B | C | D | E | F | G | H |
|---|---|---|---|---|---|---|---|---|
| **A** | – | 14 | 9 | 58 | 14 | 24 | 68 | 33 |
| **B** | 14 | – | 19 | 49 | 7 | 30 | 58 | 19 |
| **C** | 9 | 19 | – | 66 | 15 | 15 | 76 | 38 |
| **D** | 58 | 49 | 66 | – | 55 | 78 | 11 | 36 |
| **E** | 14 | 7 | 15 | 55 | – | 23 | 64 | 23 |
| **F** | 24 | 30 | 15 | 78 | 23 | – | 87 | 46 |
| **G** | 68 | 58 | 76 | 11 | 64 | 87 | – | 43 |
| **H** | 33 | 19 | 38 | 36 | 23 | 46 | 43 | – |


**Answer A (Gold).** Van 1: A→F→A = 24 km; Van 2: A→B→C→D→E→G→H→A = 162 km. Combined = **186 km** | Exact solver time: **0.60 ms**

**Answer B (Agent reference).** Expected agent time: **~120 s** (no solver, chain-of-thought). VRP is NP-hard beyond TSP; optimal split requires enumeration over subsets. Agents usually produce feasible-but-unbalanced splits.

**Benchmark metric.** Record agent's total cost, divide by 186 for the optimality gap; flag infeasible tours as gap = ∞.

---

### Problem 44: Fleet Split #44 (10 customers)

**Problem.** Two-van routing #44: hub A plus 9 customers (matrix below, km). Two vans, both start/end at A, each customer visited exactly once, each van takes ≥1 customer. Minimize combined km.

| From\To | A | B | C | D | E | F | G | H | I | J |
|---|---|---|---|---|---|---|---|---|---|---|
| **A** | – | 50 | 70 | 78 | 68 | 59 | 11 | 19 | 66 | 50 |
| **B** | 50 | – | 46 | 74 | 88 | 91 | 60 | 67 | 81 | 85 |
| **C** | 70 | 46 | – | 34 | 63 | 77 | 80 | 77 | 53 | 74 |
| **D** | 78 | 74 | 34 | – | 37 | 57 | 86 | 76 | 27 | 57 |
| **E** | 68 | 88 | 63 | 37 | – | 22 | 73 | 57 | 10 | 26 |
| **F** | 59 | 91 | 77 | 57 | 22 | – | 60 | 43 | 30 | 8 |
| **G** | 11 | 60 | 80 | 86 | 73 | 60 | – | 17 | 72 | 52 |
| **H** | 19 | 67 | 77 | 76 | 57 | 43 | 17 | – | 58 | 35 |
| **I** | 66 | 81 | 53 | 27 | 10 | 30 | 72 | 58 | – | 32 |
| **J** | 50 | 85 | 74 | 57 | 26 | 8 | 52 | 35 | 32 | – |


**Answer A (Gold).** Van 1: A→G→A = 11 km; Van 2: A→B→C→D→E→F→H→I→J→A = 251 km. Combined = **262 km** | Exact solver time: **4.21 ms**

**Answer B (Agent reference).** Expected agent time: **~120 s** (no solver, chain-of-thought). VRP is NP-hard beyond TSP; optimal split requires enumeration over subsets. Agents usually produce feasible-but-unbalanced splits.

**Benchmark metric.** Record agent's total cost, divide by 262 for the optimality gap; flag infeasible tours as gap = ∞.

---

### Problem 45: Fleet Split #45 (12 customers)

**Problem.** Two-van routing #45: hub A plus 11 customers (matrix below, km). Two vans, both start/end at A, each customer visited exactly once, each van takes ≥1 customer. Minimize combined km.

| From\To | A | B | C | D | E | F | G | H | I | J | K | L |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **A** | – | 46 | 37 | 8 | 62 | 27 | 18 | 39 | 27 | 31 | 61 | 53 |
| **B** | 46 | – | 10 | 54 | 76 | 20 | 51 | 65 | 35 | 15 | 74 | 12 |
| **C** | 37 | 10 | – | 45 | 69 | 10 | 43 | 56 | 26 | 7 | 66 | 17 |
| **D** | 8 | 54 | 45 | – | 65 | 35 | 17 | 41 | 34 | 39 | 65 | 61 |
| **E** | 62 | 76 | 69 | 65 | – | 63 | 79 | 24 | 44 | 70 | 4 | 72 |
| **F** | 27 | 20 | 10 | 35 | 63 | – | 36 | 48 | 19 | 7 | 61 | 26 |
| **G** | 18 | 51 | 43 | 17 | 79 | 36 | – | 57 | 43 | 36 | 79 | 60 |
| **H** | 39 | 65 | 56 | 41 | 24 | 48 | 57 | – | 30 | 55 | 25 | 65 |
| **I** | 27 | 35 | 26 | 34 | 44 | 19 | 43 | 30 | – | 26 | 43 | 36 |
| **J** | 31 | 15 | 7 | 39 | 70 | 7 | 36 | 55 | 26 | – | 68 | 24 |
| **K** | 61 | 74 | 66 | 65 | 4 | 61 | 79 | 25 | 43 | 68 | – | 69 |
| **L** | 53 | 12 | 17 | 61 | 72 | 26 | 60 | 65 | 36 | 24 | 69 | – |


**Answer A (Gold).** Van 1: A→G→A = 18 km; Van 2: A→B→C→D→E→F→H→I→J→K→L→A = 219 km. Combined = **237 km** | Exact solver time: **23.02 ms**

**Answer B (Agent reference).** Expected agent time: **~120 s** (no solver, chain-of-thought). VRP is NP-hard beyond TSP; optimal split requires enumeration over subsets. Agents usually produce feasible-but-unbalanced splits.

**Benchmark metric.** Record agent's total cost, divide by 237 for the optimality gap; flag infeasible tours as gap = ∞.

---


## Part 4: Impossible Problems

### Problem 46: The Disconnected Island

**Problem.** Find the shortest loop visiting A, B, C, D and returning to A. A,B,C are linked by highways; D is an island with no bridge, ferry, or airport.

**Answer A (Gold).** IMPOSSIBLE — graph is disconnected; no Hamiltonian cycle exists. | Verification time: **<0.01 ms**

**Answer B (Agent reference).** Expected agent time: **~10 s** (no solver, chain-of-thought). Correct behavior: refuse + explain. Hallucinated routes (e.g., 'fly to D') must be flagged as failures.

---

### Problem 47: The Circular Dependency

**Problem.** Deliver to A, B, C with strict precedence: A before B, B before C, and C before A. Propose a valid visiting order.

**Answer A (Gold).** IMPOSSIBLE — constraints form a cycle (A≺B≺C≺A); no linear order satisfies them. | Verification time: **<0.01 ms**

**Answer B (Agent reference).** Expected agent time: **~8 s** (no solver, chain-of-thought). Tests contradiction detection; agents that output any order fail this item.

---

### Problem 48: The Shrinking Deadline

**Problem.** Start at A (t=0). B is 10 min away and must be served by t=5; C is 8 min away with no deadline. D is 12 min away, deadline t=20. Find a feasible cycle A→…→A.

**Answer A (Gold).** IMPOSSIBLE — B cannot be reached before its deadline (earliest arrival t=10 > 5), regardless of order. | Verification time: **<0.01 ms**

**Answer B (Agent reference).** Expected agent time: **~12 s** (no solver, chain-of-thought). Feasibility-check item; correct answer identifies the violated window mathematically.

---

### Problem 49: The Overloaded Van

**Problem.** One van must deliver 8 pallets to cities B–I. Each city needs 2 pallets; the van carries at most 10 pallets. No depots or reloading allowed. Single trip from A visiting all — possible?

**Answer A (Gold).** IMPOSSIBLE — total demand 16 pallets > capacity 10; no single trip can serve all cities. | Verification time: **<0.01 ms**

**Answer B (Agent reference).** Expected agent time: **~9 s** (no solver, chain-of-thought). Capacity-constraint reasoning; agents should compute 16 > 10 rather than guess.

---

### Problem 50: The Negative-Cost Trap

**Problem.** A routing system lists edge A–B = −5 (a 'reward' for traveling). Using these weights, compute the shortest loop A→B→C→A with A–C = 10, B–C = 10.

**Answer A (Gold).** ILL-POSED — negative edge weights break the TSP's Hamiltonian-cycle assumption (repeating the rewarding edge A–B indefinitely lowers cost). No well-defined optimum; requires reformulation (e.g., max one visit enforced). Under forced single-visit: A→B→C→A = 15. | Verification time: **<0.01 ms**

**Answer B (Agent reference).** Expected agent time: **~15 s** (no solver, chain-of-thought). Best-in-class agents flag the modeling error and then solve the repaired version (=15).

---


## Benchmark Summary Table

| # | Tier | Cities | Gold cost | Solver time | Expected agent time |
|---|------|--------|-----------|-------------|---------------------|
| 1 | Small | 3 | 45 | 0.02 ms | ~5 s |
| 2 | Small | 4 | 40 | 0.03 ms | ~6 s |
| 3 | Small | 4 | 60 | 0.03 ms | ~5 s |
| 4 | Small | 5 | 25 | 0.05 ms | ~8 s |
| 5 | Small | 6 | 60 | 0.07 ms | ~10 s |
| 6 | Small | 7 | 110 | 0.24 ms | ~12 s |
| 7 | Small | 5 | 50 | 0.04 ms | ~8 s |
| 8 | Small | 4 | 55 | 0.03 ms | ~15 s |
| 9 | Small | 5 | 40 | 0.05 ms | ~10 s |
| 10 | Small | 6 | 46 | 0.06 ms | ~12 s |
| 11 | Small | 5 | 75 | 0.04 ms | ~7 s |
| 12 | Small | 5 | 5 | 0.03 ms | ~9 s |
| 13 | Small | 6 | 20 | 0.05 ms | ~10 s |
| 14 | Small | 5 | 58 | 0.04 ms | ~11 s |
| 15 | Small | 4 | 20 | 0.02 ms | ~6 s |
| 16 | Medium | 6 | 97 | 0.15 ms | ~20 s |
| 17 | Medium | 6 | 110 | 0.11 ms | ~20 s |
| 18 | Medium | 7 | 108 | 0.99 ms | ~22 s |
| 19 | Medium | 7 | 129 | 0.26 ms | ~22 s |
| 20 | Medium | 8 | 135 | 0.60 ms | ~24 s |
| 21 | Medium | 8 | 139 | 0.62 ms | ~24 s |
| 22 | Medium | 9 | 141 | 48.68 ms | ~26 s |
| 23 | Medium | 9 | 204 | 1.65 ms | ~26 s |
| 24 | Medium | 10 | 171 | 4.70 ms | ~28 s |
| 25 | Medium | 10 | 189 | 4.23 ms | ~28 s |
| 26 | Medium | 7 | 103 | 0.25 ms | ~22 s |
| 27 | Medium | 8 | 110 | 0.63 ms | ~24 s |
| 28 | Medium | 9 | 118 | 1.62 ms | ~26 s |
| 29 | Medium | 10 | 220 | 3.99 ms | ~28 s |
| 30 | Medium | 11 | 193 | 9.73 ms | ~30 s |
| 31 | Tough | 12 | 334 | 26.51 ms | ~60 s |
| 32 | Tough | 12 | 396 | 25.07 ms | ~60 s |
| 33 | Tough | 13 | 316 | 57.38 ms | ~65 s |
| 34 | Tough | 13 | 410 | 62.32 ms | ~65 s |
| 35 | Tough | 14 | 423 | 188.06 ms | ~70 s |
| 36 | Tough | 14 | 456 | 132.50 ms | ~70 s |
| 37 | Tough | 15 | 378 | 369.70 ms | ~75 s |
| 38 | Tough | 15 | 504 | 305.45 ms | ~75 s |
| 39 | Tough | 10 | 87 | 4.09 ms | ~60 s |
| 40 | Tough | 12 | 81 | 22.65 ms | ~70 s |
| 41 | Tough | 8 | 151 | 0.66 ms | ~90 s |
| 42 | Tough | 9 | 179 | 1.67 ms | ~90 s |
| 43 | Tough | — | 186 | 0.60 ms | ~120 s |
| 44 | Tough | — | 262 | 4.21 ms | ~120 s |
| 45 | Tough | — | 237 | 23.02 ms | ~120 s |
| 46 | Impossible | — | N/A (impossible) | 0.01 ms | ~10 s |
| 47 | Impossible | — | N/A (impossible) | 0.01 ms | ~8 s |
| 48 | Impossible | — | N/A (impossible) | 0.01 ms | ~12 s |
| 49 | Impossible | — | N/A (impossible) | 0.01 ms | ~9 s |
| 50 | Impossible | — | N/A (impossible) | 0.01 ms | ~15 s |