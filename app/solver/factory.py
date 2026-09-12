from __future__ import annotations

import os
from typing import Callable

from app.agents.traces import ThinkTracer
from app.solver.agents import make_solver_factory
from app.solver.llm import make_llm_solver_factory
from app.solver.problems import RoutingProblem


def build_solver_factory(
    problem: RoutingProblem,
    *,
    trace: ThinkTracer | None = None,
) -> Callable:
    """Return the pool's solver factory for a problem.

    Deterministic offline by default. Set ``SOLVER_ADAPTER=llm`` (plus LLM_* env vars
    from a gitignored ``.env``) to swap in the real model-backed LlmAgent adapter.
    """
    adapter = os.environ.get("SOLVER_ADAPTER", "deterministic")
    if adapter == "llm":
        return make_llm_solver_factory(problem, trace=trace)
    return make_solver_factory(problem, trace=trace)