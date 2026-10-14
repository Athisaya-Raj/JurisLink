"""Helpers to convert MongoDB documents into JSON-safe API responses."""
from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional

from bson import ObjectId


def json_value(value: Any) -> Any:
    """Convert an arbitrary BSON/DB value to a JSON-safe Python value.

    Handles ``ObjectId``, ``bytes``, and ``datetime``/``date`` wherever they
    appear (not only at the top level), so a stray identifier never leaks into
    an API response.
    """
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, bytes):
        return value.decode("utf-8", "ignore")
    if isinstance(value, dt.datetime):
        return value.isoformat()
    if isinstance(value, dt.date):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: json_value(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_value(item) for item in value]
    return value


def serialize_doc(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Recursively serialize a MongoDB document for a JSON response.

    * ``_id`` is exposed as ``id`` (a string).
    * All other values pass through :func:`json_value`.
    """
    if doc is None:
        return None
    out: Dict[str, Any] = {}
    for key, value in doc.items():
        if key == "_id":
            out["id"] = str(value)
        else:
            out[key] = json_value(value)
    return out


def serialize_docs(docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [serialize_doc(d) for d in docs if d is not None]


def public_lawyer(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Return the subset of a lawyer document safe/meaningful for the UI.

    ``bar_registration``/``email``/``phone`` are synthetic demo data; we keep
    them but never present them as independently verified credentials.
    """
    if doc is None:
        return None
    return serialize_doc(doc)
