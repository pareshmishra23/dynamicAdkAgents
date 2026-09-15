from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.agents import router as agents_router
from app.api.execution import router as execution_router
from app.api.mcp_servers import router as mcp_servers_router
from app.api.tools import router as tools_router
from app.config.settings import Settings
from app.repository.agent_repository import AgentRepository
from app.repository.database import H2Database
from app.repository.mcp_server_repository import McpServerRepository
from app.repository.tool_repository import ToolRepository
from app.service.agent_service import AgentService
from app.service.errors import DuplicateError, NotFoundError
from app.service.mcp_server_service import McpServerService
from app.service.tool_service import ToolService


def create_app(db: H2Database | None = None, settings: Settings | None = None) -> FastAPI:
    config = settings or Settings()
    database = db or H2Database(
        url=config.h2_url,
        jar_path=config.h2_jar_path,
        user=config.h2_user,
        password=config.h2_password,
    )
    database.ensure_schema()

    mcp_server_repository = McpServerRepository(database)
    agent_repository = AgentRepository(database)
    tool_repository = ToolRepository(database)

    app = FastAPI(title="ADK Registry & Observability Control Plane", version="0.1.0")
    app.state.database = database
    app.state.services = {
        "mcp_servers": McpServerService(mcp_server_repository),
        "agents": AgentService(agent_repository),
        "tools": ToolService(tool_repository),
    }
    app.include_router(mcp_servers_router, prefix="/api/v1")
    app.include_router(agents_router, prefix="/api/v1")
    app.include_router(tools_router, prefix="/api/v1")
    app.include_router(execution_router, prefix="/api/v1")

    # Mount UI static web directory
    web_dir = Path(__file__).resolve().parents[1] / "web"
    web_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/ui", StaticFiles(directory=str(web_dir), html=True), name="ui")

    @app.get("/", include_in_schema=False)
    def index() -> RedirectResponse:
        return RedirectResponse(url="/ui/")

    @app.exception_handler(NotFoundError)
    async def handle_not_found(request: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(DuplicateError)
    async def handle_duplicate(request: Request, exc: DuplicateError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok", "registry": "ready"}

    return app


def main() -> None:
    import uvicorn

    config = Settings()
    uvicorn.run(create_app(settings=config), host=config.host, port=config.port)


if __name__ == "__main__":
    main()