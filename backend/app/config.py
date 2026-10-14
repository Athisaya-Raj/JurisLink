"""Application configuration.

All values are read from environment variables (optionally supplied through a
local ``.env`` file). No secrets should ever be committed to version control.
"""
from __future__ import annotations

import os
from pathlib import Path

# Load a local ``.env`` file if present (python-dotenv is an optional helper).
try:  # pragma: no cover - dotenv loading is best-effort
    from dotenv import load_dotenv

    _BACKEND_DIR = Path(__file__).resolve().parent.parent  # backend/
    load_dotenv(_BACKEND_DIR / ".env")
except Exception:  # pragma: no cover
    pass


def _env(name: str, default: str = "") -> str:
    value = os.getenv(name)
    return value if value not in (None, "") else default


class Settings:
    """Typed view over the process environment."""

    # --- MongoDB -----------------------------------------------------------
    MONGODB_URI: str = _env("MONGODB_URI", "mongodb://localhost:27017")
    DATABASE_NAME: str = _env("DATABASE_NAME", "jurislink")

    # --- JWT authentication -------------------------------------------------
    JWT_SECRET_KEY: str = _env(
        "JWT_SECRET_KEY",
        "jurislink-local-development-secret-change-me-0123456789",
    )
    JWT_ALGORITHM: str = _env("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(_env("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

    # --- Server / CORS ------------------------------------------------------
    FRONTEND_URL: str = _env("FRONTEND_URL", "http://localhost:5173")
    BACKEND_HOST: str = _env("BACKEND_HOST", "127.0.0.1")
    BACKEND_PORT: int = int(_env("BACKEND_PORT", "8000"))

    # --- Demo account identity mapping --------------------------------------
    # The ``lawyer`` demo account resolves to this real record in lawyer_temp.
    DEMO_LAWYER_ID: str = _env("DEMO_LAWYER_ID", "LAW-FAM01-01")
    # The ``user`` demo account resolves to this stored user_id.
    DEMO_USER_ID: str = _env("DEMO_USER_ID", "demo-user")

    # --- Demo initialization / seeding --------------------------------------
    # When true, the development-only demo endpoints (e.g. seed-demo) are
    # reachable. Set to false in any non-local environment.
    ENABLE_DEMO_ENDPOINTS: bool = _env("ENABLE_DEMO_ENDPOINTS", "true").lower() in (
        "1", "true", "yes", "on",
    )
    # Stable id used by the idempotent demo-seed routine.
    DEMO_SEED_CASE_ID: str = _env("DEMO_SEED_CASE_ID", "DEMO-CASE-INVITE-001")

    # --- NLP classification -------------------------------------------------
    MODEL_CACHE_DIR: str = _env(
        "MODEL_CACHE_DIR",
        str(Path(__file__).resolve().parent / "services" / ".model_cache"),
    )
    MIN_DESCRIPTION_LENGTH: int = int(_env("MIN_DESCRIPTION_LENGTH", "10"))
    REVIEW_CONFIDENCE_THRESHOLD: float = float(
        _env("REVIEW_CONFIDENCE_THRESHOLD", "0.05")
    )


settings = Settings()
