"""NLP classification tests (unit + via API)."""
from __future__ import annotations

import pytest

from app.services import classification
from app.services.classification import ClassificationError


def test_model_diagnostics_ready(client):
    resp = client.get("/admin/model-info")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ready"] is True
    assert body["num_categories"] == 25
    assert "accuracy" in body["metrics"]


def test_category_mapping_matches_legal_categories():
    mapping = classification.load_category_map()
    assert len(mapping) == 25
    assert mapping.get("PRO02") == "Rental and Tenancy Disputes"
    assert mapping.get("FAM01") == "Marriage and Family Disputes"


def test_valid_text_produces_prediction():
    result = classification.predict(
        "My landlord refuses to return my rental deposit even though I vacated "
        "the apartment and completed the agreement."
    )
    assert result["category_id"] == "PRO02"
    assert result["category_name"] == "Rental and Tenancy Disputes"
    assert 0.0 <= result["confidence"] <= 1.0
    assert result["explanation"]


def test_family_text_produces_prediction():
    result = classification.predict(
        "My spouse and I have a serious disagreement about our marital rights "
        "and responsibilities and I need legal guidance."
    )
    assert result["category_id"] == "FAM01"


def test_empty_text_rejected():
    with pytest.raises(ClassificationError):
        classification.predict("")


def test_too_short_text_rejected():
    with pytest.raises(ClassificationError):
        classification.predict("help me")


def test_missing_data_reports_error(monkeypatch):
    # Simulate empty training data: should raise a clear diagnostic, not invent.
    monkeypatch.setattr(classification, "load_training_data", lambda: ([], [], 0, 0))
    with pytest.raises(ClassificationError) as exc:
        classification.train(force=True)
    assert "case_training_data_temp" in str(exc.value)
