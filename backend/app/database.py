"""MongoDB connection, collection access, and index management.

The application is strictly tied to the pre-existing ``jurislink`` database and
its five imported collections. If the connection cannot be established the
error is surfaced (never silently swapped for an in-memory store).
"""
from __future__ import annotations

import logging
from typing import Optional

from pymongo import ASCENDING, MongoClient
from pymongo.errors import PyMongoError

from .config import settings

logger = logging.getLogger("jurislink.database")

_client: Optional[MongoClient] = None
_db = None

# The five imported collections (exact names — do not rename or recreate).
COLLECTIONS = [
    "legal_categories_temp",
    "lawyer_temp",
    "case_training_data_temp",
    "case_temp",
    "appointment_temp",
]

# Collections created and managed by the application itself (idempotently via
# index creation). These are NOT part of the required imported datasets.
APP_COLLECTIONS = [
    "case_invitation_temp",
    "progress_note_temp",
]


def get_client() -> MongoClient:
    """Return a shared MongoClient (lazily created)."""
    global _client
    if _client is None:
        _client = MongoClient(
            settings.MONGODB_URI,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
        )
    return _client


def get_db():
    """Return the ``jurislink`` database handle (lazily created)."""
    global _db
    if _db is None:
        _db = get_client()[settings.DATABASE_NAME]
    return _db


def connect() -> None:
    """Verify connectivity to MongoDB and the expected database.

    Raises ``PyMongoError`` (or a subclass) when MongoDB is unavailable.
    """
    client = get_client()
    client.admin.command("ping")
    db = get_db()
    # Confirm the configured database resolves to something with our collections.
    existing = set(db.list_collection_names())
    missing = [name for name in COLLECTIONS if name not in existing]
    if missing:
        raise RuntimeError(
            f"Database '{settings.DATABASE_NAME}' is missing required collections: "
            f"{', '.join(missing)}. Verify the JSON datasets were imported."
        )
    return db


def close() -> None:
    """Close the shared client (used on shutdown / in tests)."""
    global _client, _db
    if _client is not None:
        _client.close()
        _client = None
        _db = None


def ensure_indexes(db=None) -> None:
    """Create the indexes the application relies on (idempotent).

    Index creation is defensive: a single failed index is logged rather than
    aborting startup, so pre-existing seed data never blocks the app.
    """
    db = db or get_db()

    def _safe(coll_name: str, keys, **kwargs):
        try:
            db[coll_name].create_index(keys, **kwargs)
        except PyMongoError as exc:  # pragma: no cover - depends on data
            logger.warning("Could not create index on %s: %s", coll_name, exc)

    _safe("legal_categories_temp", [("category_id", ASCENDING)], unique=True, name="uq_category_id")
    _safe("lawyer_temp", [("lawyer_id", ASCENDING)], unique=True, name="uq_lawyer_id")
    _safe("lawyer_temp", [("specializations", ASCENDING)], name="ix_lawyer_specializations")
    _safe("case_training_data_temp", [("category_id", ASCENDING)], name="ix_train_category")

    _safe("case_temp", [("case_id", ASCENDING)], unique=True, name="uq_case_id")
    _safe("case_temp", [("user_id", ASCENDING)], name="ix_case_user")
    _safe("case_temp", [("assigned_lawyer_id", ASCENDING)], name="ix_case_lawyer")
    # Idempotency key for duplicate-submission protection.
    _safe(
        "case_temp",
        [("client_request_id", ASCENDING)],
        unique=True,
        partialFilterExpression={"client_request_id": {"$exists": True}},
        name="uq_case_client_request",
    )

    _safe("appointment_temp", [("appointment_id", ASCENDING)], unique=True, name="uq_appointment_id")
    _safe("appointment_temp", [("user_id", ASCENDING)], name="ix_appt_user")
    _safe("appointment_temp", [("lawyer_id", ASCENDING)], name="ix_appt_lawyer")
    _safe("appointment_temp", [("case_id", ASCENDING)], name="ix_appt_case")
    # Partial unique index prevents double-booking a slot while it is active.
    _safe(
        "appointment_temp",
        [("slot_id", ASCENDING)],
        unique=True,
        partialFilterExpression={"status": {"$in": ["requested", "booked"]}},
        name="uq_appt_slot_active",
    )

    # Case invitations (application-managed collection).
    _safe("case_invitation_temp", [("invitation_id", ASCENDING)], unique=True, name="uq_invitation_id")
    _safe("case_invitation_temp", [("lawyer_id", ASCENDING), ("status", ASCENDING)], name="ix_inv_lawyer_status")
    _safe("case_invitation_temp", [("case_id", ASCENDING)], name="ix_inv_case")
    # At most one pending invitation per case (enforces the single-active-offer model).
    _safe(
        "case_invitation_temp",
        [("case_id", ASCENDING)],
        unique=True,
        partialFilterExpression={"status": "pending"},
        name="uq_inv_case_pending",
    )

    # Progress notes (application-managed collection).
    _safe("progress_note_temp", [("progress_note_id", ASCENDING)], unique=True, name="uq_progress_note_id")
    _safe("progress_note_temp", [("case_id", ASCENDING)], name="ix_progress_case")
    _safe("progress_note_temp", [("lawyer_id", ASCENDING)], name="ix_progress_lawyer")


def collection_counts(db=None) -> dict:
    """Return a quick document count per collection (for health)."""
    db = db or get_db()
    result = {}
    for name in COLLECTIONS + APP_COLLECTIONS:
        try:
            result[name] = db[name].count_documents({})
        except PyMongoError as exc:  # pragma: no cover
            result[name] = f"error: {exc}"
    return result
