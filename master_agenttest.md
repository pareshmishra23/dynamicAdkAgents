# Master Agent Test — Routing & Constraint Reasoning Benchmark

## Small Problems (Easily Solved)

These require simple spatial reasoning and have a small combinatorial space.

### 1. The Triangle Route (3 Cities)

**Problem:** You must visit cities A, B, and C, and return to your starting point. The distances are: A to B = 10 miles, B to C = 15 miles, and C to A = 20 miles. What is the shortest route?

**Answer:** A → B → C → A. Because it's a triangle, there is only one distinct loop. Total distance = 45 miles.

### 2. The Square Matrix (4 Cities)

**Problem:** Four cities (A, B, C, D) form a perfect square. The perimeter roads (A-B, B-C, C-D, D-A) are 10 miles each. The diagonal roads (A-C, B-D) are 14 miles each. Find the optimal loop.

**Answer:** A → B → C → D → A. Sticking to the perimeter avoids the longer diagonal routes. Total distance = 40 miles.

### 3. The Linear Highway (4 Cities)

**Problem:** Cities are located at mile markers 0, 10, 20, and 30 on a single straight highway. Start at 0, visit all cities, and return to 0.

**Answer:** 0 → 10 → 20 → 30 → 0. Total distance = 60 miles (30 miles out, 30 miles back).

## Medium Problems (Challenges Context and Planning)

These problems introduce constraints and asymmetries that begin to test an agent's logical planning.

### 4. The Asymmetric One-Way Street (5 Cities)

**Problem:** You must loop through A, B, C, D, and E. The clockwise route (A→B→C→D→E→A) consists of flat one-way roads costing 5 minutes each. The counter-clockwise route goes uphill and costs 15 minutes between each city.

**Answer:** The clockwise route: A → B → C → D → E → A. Total time = 25 minutes.

### 5. The Morning Hub Constraint (6 Cities)

**Problem:** A salesman starts at City A and must visit B, C, D, E, and F (all 10 miles apart from each other). However, City C's office closes at 9:00 AM, meaning it must be the very first stop after leaving A.

**Answer:** A → C → (B/D/E/F in any order) → A. The total distance is 60 miles, but the logical constraint dictates the specific starting node.

### 6. The Hub-and-Spoke (7 Cities)

**Problem:** City A is the central hub. Cities B through G surround it in a circle. Moving from the hub to any outer city costs 5 miles. Moving between adjacent outer cities costs 20 miles.

**Answer:** To minimize distance, you should not go back and forth to the hub. The optimal path is A → B → C → D → E → F → G → A. Total distance = 5 (hub to spoke) + 100 (5 spoke-to-spoke edges) + 5 (spoke back to hub) = 110 miles.

## Tough Problems (Combinatorial Explosion)

These problems scale beyond simple logic and require advanced routing algorithms (like Gurobi or Christofides heuristics).

### 7. The 15-City Factorial

**Problem:** A logistics driver must visit 15 randomized cities in a symmetric graph and return home.

**Answer:** This requires checking (or running a heuristic against) 15! permutations, which is over 1.3 trillion distinct routes. The exact answer depends on the generated distance matrix, but it is computationally intensive.

### 8. The VRP (Vehicle Routing Problem) Split

**Problem:** 2 agents must visit 10 cities total, starting and ending at a central hub. No single agent can visit more than 6 cities, and they must perfectly balance their travel distances across asymmetric mountain terrain.

**Answer:** This is an NP-hard generalization of the TSP. It requires a dedicated solver to map two interwoven Hamiltonian cycles based on the specific terrain weights.

## Impossible Problems (Logical Contradictions)

These tests evaluate an agent's ability to recognize unsolvable scenarios rather than hallucinating an answer.

### 9. The Disconnected Island

**Problem:** Find the shortest continuous loop to visit cities A, B, C, and D. Cities A, B, and C are connected by highways. City D is on an island with no bridges, ferries, or airports.

**Answer:** Impossible. The graph is disconnected; therefore, no Hamiltonian cycle exists.

### 10. The Time-Paradox Delivery

**Problem:** You must deliver packages to A, B, and C. Due to strict dependency chains: A must be visited before B, B must be visited before C, and C must be visited before A.

**Answer:** Impossible. The constraints create an unresolvable circular dependency loop.

## Agent Benchmark Performance: How Close Are We?

Historically, language models have struggled to solve constrained combinatorial problems natively. However, based on the 2026 ConstraintBench evaluation, here is how frontier models perform on direct optimization tasks like the TSP:

- **Feasibility vs. Optimality:** The primary bottleneck for AI agents is feasibility, not optimality. The best models currently achieve only a 65.0% constraint satisfaction rate. This means they struggle to perfectly adhere to rules (like visiting every city exactly once without skipping).
- **The Optimality Gap:** Interestingly, when an agent does manage to output a valid, feasible route, that route is highly efficient. Feasible solutions generated by LLMs average 89% to 96% of the Gurobi-proven optimum.

To improve these numbers, engineers are shifting away from treating reasoning as a sequence of words and are adopting the TRRPO (TSP-Relaxed Reasoning Path Optimization) framework. This novel 2026 paradigm treats the AI's internal reasoning steps as nodes in a high-dimensional space, training the model to find the "shortest effective reasoning path" and naturally cut out redundant logic loops without relying on external rules.