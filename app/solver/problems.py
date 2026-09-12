from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Edge:
    a: str
    b: str
    cost: float


@dataclass(frozen=True)
class RoutingProblem:
    id: str
    title: str
    cities: tuple[str, ...]
    edges: tuple[Edge, ...]
    directed: bool = False
    expected: tuple[str, ...] | None = None
    expected_cost: float | None = None
    impossible: bool = False


PROBLEM_1 = RoutingProblem(
    id="1",
    title="The Triangle Route (3 Cities)",
    cities=("A", "B", "C"),
    edges=(Edge("A", "B", 10), Edge("B", "C", 15), Edge("C", "A", 20)),
    directed=False,
    expected=("A", "B", "C"),
    expected_cost=45.0,
)

PROBLEM_2 = RoutingProblem(
    id="2",
    title="The Square Matrix (4 Cities)",
    cities=("A", "B", "C", "D"),
    edges=(
        Edge("A", "B", 10),
        Edge("B", "C", 10),
        Edge("C", "D", 10),
        Edge("D", "A", 10),
        Edge("A", "C", 14),
        Edge("B", "D", 14),
    ),
    directed=False,
    expected=("A", "B", "C", "D"),
    expected_cost=40.0,
)

BENCHMARK_PROBLEMS: tuple[RoutingProblem, ...] = (PROBLEM_1, PROBLEM_2)