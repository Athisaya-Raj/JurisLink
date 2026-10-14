"""Development/diagnostic endpoints (NLP + demo seeding).

These are intended for local development and are not part of the client-facing
API. The demo-seeding endpoint is gated behind ``ENABLE_DEMO_ENDPOINTS`` so it
cannot be abused outside local development.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from ..config import settings
from ..services import classification, demo_seed
from ..services.classification import ClassificationError

router = APIRouter(tags=["admin"])


@router.get("/model-info")
def model_info():
    return classification.model_diagnostics()


@router.post("/retrain")
def retrain():
    try:
        meta = classification.train(force=True)
    except ClassificationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )
    return {"trained": True, "meta": meta}


@router.post("/seed-demo")
def seed_demo():
    if not settings.ENABLE_DEMO_ENDPOINTS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo endpoints are disabled in this environment.",
        )
    try:
        return demo_seed.seed_demo()
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
