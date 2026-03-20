from __future__ import annotations

import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.middleware.error_handler import http_exception_handler, unhandled_exception_handler
from app.middleware.rate_limit import limiter
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.routers import auth, billing, lineups, mlb, projections, simulations

_start_time = time.monotonic()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.middleware.logging_config import setup_logging
    setup_logging()
    from app.database import _use_sqlite, engine
    if _use_sqlite:
        from app.models.user import Base
        import app.models  # noqa: F401 — register all models
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    yield
    from app.database import engine as _engine
    await _engine.dispose()


app = FastAPI(
    title="Stack Sniper DFS",
    version="1.0.0",
    description="Multi-sport DFS projections and simulation platform (MLB + NFL)",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

app.add_middleware(RequestIDMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(projections.router, prefix="/api/nfl/projections", tags=["nfl-projections"])
app.include_router(simulations.router, prefix="/api/nfl/simulations", tags=["nfl-simulations"])
app.include_router(lineups.router, prefix="/api/nfl/lineups", tags=["nfl-lineups"])
app.include_router(mlb.router, prefix="/api/mlb", tags=["mlb"])
app.include_router(billing.router, prefix="/api/billing", tags=["billing"])

# Backward compat: keep old NFL routes working without /nfl/ prefix
app.include_router(projections.router, prefix="/api/projections", tags=["projections"], include_in_schema=False)
app.include_router(simulations.router, prefix="/api/simulations", tags=["simulations"], include_in_schema=False)
app.include_router(lineups.router, prefix="/api/lineups", tags=["lineups"], include_in_schema=False)


@app.get("/health")
async def health_check():
    from app.database import engine
    db_ok = False
    try:
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
            db_ok = True
    except Exception:
        pass
    return {
        "status": "ok",
        "version": "0.1.0",
        "db_connected": db_ok,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": round(time.monotonic() - _start_time, 2),
    }
