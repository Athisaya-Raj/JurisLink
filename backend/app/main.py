"""FastAPI application entry point for JurisLink."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError

from .config import settings
from .database import close, collection_counts, connect, ensure_indexes, get_db
from .routers import admin, appointments, auth, cases, dashboard, invitations, lawyers, progress
from .services import classification

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger("jurislink")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- startup -----------------------------------------------------------
    try:
        connect()
        ensure_indexes()
        logger.info("Connected to MongoDB database '%s'", settings.DATABASE_NAME)
    except Exception as exc:  # noqa: BLE001 - report, but keep /health reachable
        logger.critical("Startup database error: %s", exc)

    # Warm the classifier so the first request is fast (best-effort).
    try:
        classification.ensure_model()
        logger.info("Classification model ready.")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Classification model not ready at startup: %s", exc)

    demo_lawyer = get_db()["lawyer_temp"].find_one({"lawyer_id": settings.DEMO_LAWYER_ID})
    if demo_lawyer is None:
        logger.warning(
            "DEMO_LAWYER_ID '%s' not found in lawyer_temp; the lawyer dashboard "
            "will be empty until it is configured.",
            settings.DEMO_LAWYER_ID,
        )

    yield
    # --- shutdown ----------------------------------------------------------
    close()


app = FastAPI(
    title="JurisLink API",
    description="AI-assisted legal case intake and lawyer allocation platform.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    # Local-development frontend origins. Vite auto-increments the port when
    # one is already occupied, so both 5173 and 5174 are allowed.
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(PyMongoError)
async def database_error_handler(request: Request, exc: PyMongoError):
    logger.error("Database error while handling %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=503,
        content={"detail": "Database unavailable. Please ensure MongoDB is running."},
    )


app.include_router(auth.router, prefix="/auth")
app.include_router(cases.router, prefix="/cases")
app.include_router(invitations.router, prefix="/invitations")
app.include_router(lawyers.router, prefix="/lawyers")
app.include_router(appointments.router, prefix="/appointments")
app.include_router(dashboard.router, prefix="/dashboard")
app.include_router(progress.router, prefix="/progress")
app.include_router(admin.router, prefix="/admin")


@app.get("/health")
def health():
    payload = {
        "status": "ok",
        "service": "jurislink",
        "database": {"connected": False, "name": settings.DATABASE_NAME, "collections": {}},
        "model": classification.model_diagnostics(),
    }
    try:
        connect()
        payload["database"]["connected"] = True
        payload["database"]["collections"] = collection_counts()
    except Exception as exc:  # noqa: BLE001
        payload["status"] = "degraded"
        payload["database"]["connected"] = False
        payload["database"]["error"] = str(exc)
    return payload
