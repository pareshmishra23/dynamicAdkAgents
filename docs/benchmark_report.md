# Agent Pool Solver Benchmark Report

Run on a deterministic local pool (no model calls). Each problem solved by a
planner-decided agent pool; full thinking traces saved under `logs/problem_<n>.log`.

| # | Problem | n | Pool size | Agents | Time (ms) | Status | Rating |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | The Triangle Route (3 Cities) | 3 | 3 | graph_builder, tour_engine, route_validator | 5.3 | completed | EXCELLENT (exact enumeration) |
| 2 | The Square Matrix (4 Cities) | 4 | 3 | graph_builder, tour_engine, route_validator | 2.8 | completed | EXCELLENT (exact enumeration) |
| 3 | The Linear Highway (4 Cities) | 4 | 3 | graph_builder, tour_engine, route_validator | 3.2 | completed | EXCELLENT (exact enumeration) |
| 4 | The Asymmetric One-Way Street (5 Cities) | 5 | 3 | graph_builder, tour_engine, route_validator | 2.7 | completed | EXCELLENT (exact enumeration) |
| 5 | The Morning Hub Constraint (6 Cities) | 6 | 3 | graph_builder, tour_engine, route_validator | 3.0 | completed | EXCELLENT (exact enumeration) |
| 6 | The Hub-and-Spoke (7 Cities) | 7 | 3 | graph_builder, tour_engine, route_validator | 4.1 | completed | EXCELLENT (exact enumeration) |
| 7 | The 15-City Factorial | 15 | 4 | graph_builder, tour_engine, route_validator, optimizer | 3.3 | completed | GOOD (feasible heuristic, optimum unknown) |
| 8 | The VRP Split (2 vehicles, 10 cities) | 10 | 2 | vrp_splitter, vrp_validator | 2.7 | completed | GOOD (feasible balanced split, not proven optimal) |
| 9 | The Disconnected Island | 4 | 2 | graph_builder, route_validator | 2.8 | completed | EXCELLENT (correctly abstains / proves impossibility) |
| 10 | The Time-Paradox Delivery | 3 | 2 | dependency_checker, order_reviewer | 3.0 | completed | EXCELLENT (correctly abstains / proves impossibility) |

## Solver pattern observations

- Exact-enumeration path (n<=9) never misses the optimum; it is the reference oracle.
- Heuristic path (n>9, 15-city) uses greedy nearest-neighbor + 2-opt; optimal not proven.
- Impossibility / precedence problems route to a proof pool and abstain instead of guessing.
