from __future__ import annotations

from app.models import ToolSpec
from app.registry.policy import ToolRegistry
from app.tools.web import webfetch_handler, websearch_handler


def _noop_handler(**kwargs):  # pragma: no cover - dispatched logic lives in solver agents
    return kwargs


DEFAULT_TOOL_SPECS = (
    ToolSpec(name="matrix_build", description="build distance/cost matrix", handler=_noop_handler),
    ToolSpec(name="tour_enum", description="enumerate candidate loops", handler=_noop_handler),
    ToolSpec(name="cycle_check", description="verify Hamiltonian cycle", handler=_noop_handler),
    ToolSpec(name="prune", description="prune search space", handler=_noop_handler),
    ToolSpec(name="balance_split", description="partition city set for VRP", handler=_noop_handler),
    ToolSpec(name="capacity_check", description="verify route capacity", handler=_noop_handler),
    ToolSpec(name="order_check", description="run topological ordering check", handler=_noop_handler),
    ToolSpec(name="read_back", description="read back prior verdict", handler=_noop_handler),
    ToolSpec(
        name="websearch",
        description="search the web for live data (BEAD 7, offline-safe)",
        handler=websearch_handler,
        allowed_agent_ids=("research_agent",),
    ),
    ToolSpec(
        name="webfetch",
        description="fetch a page as plain text (BEAD 7, offline-safe)",
        handler=webfetch_handler,
        allowed_agent_ids=("research_agent",),
    ),
)


def default_tool_registry() -> ToolRegistry:
    return ToolRegistry(DEFAULT_TOOL_SPECS)