from __future__ import annotations

import uvicorn
from fastapi import FastAPI

from app.api.v1.router import router as api_v1_router
from app.core.errors import register_error_handlers
from app.core.config import get_settings
from app.core.middleware import register_middlewares
from app.core.lifespan import lifespan


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )
    register_middlewares(app)
    register_error_handlers(app)
    app.include_router(api_v1_router)
    return app


app = create_app()


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
