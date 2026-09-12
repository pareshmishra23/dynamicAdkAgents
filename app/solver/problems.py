from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Edge:
    a: str
    b: str
    cost: float


def _dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return round(math.hypot(a[0] - b[0], a[1] - b[1]), 2)


def _complete_edges(coords: dict[str, tuple[float, float]]) -> tuple[Edge, ...]:
    names = list(coords)
    edges = []
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            d = _dist(coords[a], coords[b])
            edges.append(Edge(a, b, d))
    return tuple(edges)


def _forced_edges(*triples: tuple[str, str, float]) -> tuple[Edge, ...]:
    return tuple(Edge(a, b, c) for a, b, c in triples)


@dataclass(frozen=True)
class RoutingProblem:
    id: str
    title: str
    cities: tuple[str, ...]
    edges: tuple[Edge, ...]
    directed: bool = False
    kind: str = "tsp"
    coords: dict[str, tuple[float, float]] | None = None
    precedence: tuple[tuple[str, str], ...] = ()
    first_stop_after_start: str | None = None
    impossible: bool = False
    expected: tuple[str, ...] | None = None
    expected_cost: float | None = None
    notes: str = ""


PROBLEM_1 = RoutingProblem(
    id="1",
    title="The Triangle Route (3 Cities)",
    cities=("A", "B", "C"),
    edges=_forced_edges(("A", "B", 10), ("B", "C", 15), ("C", "A", 20)),
    expected=("A", "B", "C"),
    expected_cost=45.0,
    notes="single distinct loop for n=3",
)

PROBLEM_2 = RoutingProblem(
    id="2",
    title="The Square Matrix (4 Cities)",
    cities=("A", "B", "C", "D"),
    edges=_forced_edges(
        ("A", "B", 10), ("B", "C", 10), ("C", "D", 10), ("D", "A", 10),
        ("A", "C", 14), ("B", "D", 14),
    ),
    expected=("A", "B", "C", "D"),
    expected_cost=40.0,
    notes="perimeter beats the 14-mile diagonals",
)

PROBLEM_3 = RoutingProblem(
    id="3",
    title="The Linear Highway (4 Cities)",
    cities=("0", "10", "20", "30"),
    edges=_forced_edges(("0", "10", 10), ("10", "20", 10), ("20", "30", 10), ("30", "0", 30)),
    expected=("0", "10", "20", "30"),
    expected_cost=60.0,
    notes="out-and-back along a single highway",
)

_PROBLEM_4_ORDER = ("A", "B", "C", "D", "E")
PROBLEM_4 = RoutingProblem(
    id="4",
    title="The Asymmetric One-Way Street (5 Cities)",
    cities=_PROBLEM_4_ORDER,
    edges=tuple(
        Edge(_PROBLEM_4_ORDER[i], _PROBLEM_4_ORDER[(i + 1) % 5], 5)
        for i in range(5)
    ) + tuple(
        Edge(_PROBLEM_4_ORDER[(i + 1) % 5], _PROBLEM_4_ORDER[i], 15)
        for i in range(5)
    ),
    directed=True,
    expected=("A", "B", "C", "D", "E"),
    expected_cost=25.0,
    notes="clockwise 5min vs counter-clockwise 15min",
)

_PROBLEM_5_CITIES = ("A", "B", "C", "D", "E", "F")
PROBLEM_5 = RoutingProblem(
    id="5",
    title="The Morning Hub Constraint (6 Cities)",
    cities=_PROBLEM_5_CITIES,
    edges=_forced_edges(
        *((a, b, 10) for i, a in enumerate(_PROBLEM_5_CITIES) for b in _PROBLEM_5_CITIES[i + 1 :])
    ),
    first_stop_after_start="C",
    expected=("A", "C", "B", "D", "E", "F"),
    expected_cost=60.0,
    notes="office C closes at 9:00 -> must be the first stop after A",
)

_PROBLEM_6_OUTER = ("B", "C", "D", "E", "F", "G")
PROBLEM_6 = RoutingProblem(
    id="6",
    title="The Hub-and-Spoke (7 Cities)",
    cities=("A",) + _PROBLEM_6_OUTER,
    edges=_forced_edges(
        *[("A", c, 5) for c in _PROBLEM_6_OUTER],
        *[
            (_PROBLEM_6_OUTER[i], _PROBLEM_6_OUTER[(i + 1) % 6], 20)
            for i in range(6)
        ],
    ),
    expected=("A", "B", "C", "D", "E", "F", "G"),
    expected_cost=110.0,
    notes="don't bounce back to the hub; walk the ring once",
)

def _circle_coords(count: int, radius: float, tilt: float, jitter_seed: int) -> dict[str, tuple[float, float]]:
    return {
        f"c{i + 1}": (
            round(radius * math.cos(tilt + 2 * math.pi * i / count) + ((i * jitter_seed) % 50) - 25, 2),
            round(radius * math.sin(tilt + 2 * math.pi * i / count) + ((i * jitter_seed * 7) % 50) - 25, 2),
        )
        for i in range(count)
    }

PROBLEM_7 = RoutingProblem(
    id="7",
    title="The 15-City Factorial",
    cities=tuple(f"c{i + 1}" for i in range(15)),
    edges=_complete_edges(_circle_coords(15, 1000.0, 0.35, 37)),
    kind="tsp",
    coords=_circle_coords(15, 1000.0, 0.35, 37),
    notes="NP-hard; brute force infeasible -> heuristic pool",
)

_PROBLEM_8_HUB = "hub"
_PROBLEM_8_COORDS = {"hub": (0.0, 0.0), **_circle_coords(9, 100.0, 0.7, 19)}
PROBLEM_8 = RoutingProblem(
    id="8",
    title="The VRP Split (2 vehicles, 10 cities)",
    cities=tuple(_PROBLEM_8_COORDS),
    edges=_complete_edges(_PROBLEM_8_COORDS),
    kind="vrp",
    coords=_PROBLEM_8_COORDS,
    notes="split city set so no vehicle exceeds 6 stops, balance distance",
)

PROBLEM_9 = RoutingProblem(
    id="9",
    title="The Disconnected Island",
    cities=("A", "B", "C", "D"),
    edges=_forced_edges(("A", "B", 10), ("B", "C", 10), ("C", "A", 10)),
    impossible=True,
    notes="island D has no bridges -> graph disconnected, no Hamiltonian cycle",
)

PROBLEM_10 = RoutingProblem(
    id="10",
    title="The Time-Paradox Delivery",
    cities=("A", "B", "C"),
    edges=(),
    kind="precedence",
    precedence=(("A", "B"), ("B", "C"), ("C", "A")),
    notes="A before B, B before C, C before A -> circular dependency",
)

BENCHMARK_PROBLEMS: tuple[RoutingProblem, ...] = (
    PROBLEM_1, PROBLEM_2, PROBLEM_3, PROBLEM_4, PROBLEM_5,
    PROBLEM_6, PROBLEM_7, PROBLEM_8, PROBLEM_9, PROBLEM_10,
)