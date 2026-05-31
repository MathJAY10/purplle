from __future__ import annotations

from uuid import uuid4

from fastapi import FastAPI, Request


def register_middlewares(app: FastAPI) -> None:
    @app.middleware("http")
    async def trace_id_middleware(request: Request, call_next):
        trace_id = request.headers.get("X-Trace-Id") or str(uuid4())
        request.state.trace_id = trace_id
        response = await call_next(request)
        response.headers["X-Trace-Id"] = trace_id
        return response