"""FastAPI application — Terra.OS local API (127.0.0.1 only)."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from terra_shared.errors import TerraError
from .routers import health, zwiad, documents, estimator, engine, rfq, chat, module3, system


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    yield


app = FastAPI(
    title="Terra.OS API",
    version="0.1.0",
    description="Local-only REST API for Terra.OS earthworks management system.",
    lifespan=lifespan,
    docs_url="/docs" if os.getenv("ENVIRONMENT", "dev") == "dev" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "tauri://localhost"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(TerraError)
async def terra_error_handler(request: Request, exc: TerraError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
    )


app.include_router(health.router)
app.include_router(zwiad.router)
app.include_router(documents.router)
app.include_router(estimator.router)
app.include_router(engine.router)
app.include_router(rfq.router)
app.include_router(chat.router)
app.include_router(module3.router)
app.include_router(system.router)
