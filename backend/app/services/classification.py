"""NLP legal-case classification (hybrid, explainable).

The model is trained from the labeled examples in ``case_training_data_temp``
and *augmented* with the canonical category definitions in
``legal_categories_temp`` (name + description + keywords). The imported data is
synthetic and templated (~4 distinct phrasings per category), so the canonical
keywords are a high-quality, existing source of signal that the raw examples
lack. Augmentation is documented and clearly distinguished from original data.

Pipeline:
    text cleaning (lowercase, punctuation, contraction expansion)
  -> TF-IDF features: word unigrams+bigrams  UNION  character (char_wb) n-grams
  -> calibrated Logistic Regression  (``predict_proba``)
  -> hybrid scoring: model probability combined with a canonical keyword/phrase
     overlap score (documented high-precision patterns).

The model + vectorizer + canonical label mapping are cached to disk and
re-trained automatically when the data or pipeline changes.
"""
from __future__ import annotations

import hashlib
import json
import logging
import pickle
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion

from ..config import settings
from ..database import get_db

logger = logging.getLogger("jurislink.classification")


class ClassificationError(RuntimeError):
    """Raised when classification cannot be performed meaningfully."""


# Bump this whenever the pipeline/features/hybrid logic changes so that stale
# cached artifacts are invalidated.
PIPELINE_VERSION = "3"

# Hybrid combination weights (model vs. keyword overlap).
_MODEL_WEIGHT = 0.6
_KEYWORD_WEIGHT = 0.4

# Review threshold on the combined decision margin (top score - second score).
_REVIEW_MARGIN_THRESHOLD = 0.05

# High-precision patterns for terms that the canonical ``keywords`` do not
# cover. This is a small, curated, documented addition — it only nudges the
# combined score and never overrides a strong model prediction on its own.
_CURATED_PATTERNS: Dict[str, List[str]] = {
    "CRI01": ["assault", "threatened", "threatening", "attacked", "theft",
              "stolen", "robbed", "arrested", "bail", "police complaint",
              "criminal case", "offence", "offense"],
    "FRA01": ["forged", "forgery", "cheated", "cheating", "deceived",
              "defrauded", "misrepresented", "deception"],
    "PRO02": ["landlord", "tenant", "eviction", "lease", "security deposit",
              "rental deposit", "rent agreement", "rent"],
    "PRO01": ["boundary", "encroachment", "title deed", "land ownership",
              "property ownership", "land dispute", "land"],
    "PRO03": ["inheritance", "succession", "probate", "heir", "estate dispute",
              "will dispute", "inherited"],
    "CON01": ["breach", "breached", "contract", "agreement", "violated",
              "failed to complete", "non payment", "non-payment"],
    "CYB01": ["phishing", "hacked", "online scam", "identity theft",
              "cyber fraud", "cybercrime"],
    "MED01": ["medical negligence", "malpractice", "hospital", "treatment",
              "surgery"],
    "IPR01": ["copyright", "trademark", "patent", "intellectual property"],
    "EMP01": ["termination", "terminated", "dismissed", "fired", "harassment",
              "workplace", "employer"],
    "EMP02": ["salary", "wages", "unpaid", "bonus", "overtime", "final settlement"],
    "BANK01": ["bank", "loan", "interest rate", "banking"],
    "INS01": ["insurance", "insurer", "policy", "premium", "claim"],
    "IMM01": ["visa", "immigration", "passport", "residency"],
    "TAX01": ["tax", "taxation", "assessment", "gst", "income tax"],
    "ENV01": ["pollution", "environmental", "waste", "emission"],
    "EDU01": ["university", "college", "admission", "examination", "school"],
    "FAM01": ["spouse", "marriage", "marital", "family dispute"],
    "FAM02": ["divorce", "separation", "marital dissolution"],
    "FAM03": ["custody", "guardianship", "parenting", "visitation"],
    "FAM04": ["alimony", "maintenance", "spousal support"],
    "CON02": ["consumer", "defective product", "refund", "unfair trade",
              "faulty product"],
    "COM01": ["shareholder", "director", "corporate governance", "company"],
    "COM02": ["incorporation", "registration", "register", "compliance", "startup"],
    "CIV01": ["debt recovery", "civil suit", "damages", "civil claim"],
}

# High-severity violence terms that legally dominate an overlapping civil or
# property description (e.g. "threatened to assault me during a boundary
# dispute" is a criminal matter, not a property dispute).
_DOMINANT_PHRASES = {
    "assault", "attacked", "murder", "rape", "kidnapping",
    "threatened", "threatening",
}

# Strong fraud terms that should outweigh a generic overlap word.
_HIGH_WEIGHT_PHRASES = {
    "forged", "forgery", "cheated", "cheating", "defrauded",
    "deceived", "deception", "theft", "stolen", "robbed",
}

_CONTRACTIONS = {
    "doesnt": "does not", "dont": "do not", "isnt": "is not", "arent": "are not",
    "cant": "cannot", "wont": "will not", "didnt": "did not", "couldnt": "could not",
    "wouldnt": "would not", "shouldnt": "should not", "wasnt": "was not",
    "werent": "were not", "hasnt": "has not", "havent": "have not",
    "im": "i am", "ive": "i have", "id": "i would", "ill": "i will",
    "refuses": "refuses", "refused": "refused",
}


# --------------------------------------------------------------------------
# Text preprocessing
# --------------------------------------------------------------------------
def clean_text(text: str) -> str:
    """Normalize a legal description for feature extraction.

    Lowercases, removes punctuation, collapses whitespace, and expands common
    contractions so negations and pronouns are preserved as meaningful tokens.
    """
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    tokens = [_CONTRACTIONS.get(t, t) for t in text.split()]
    return " ".join(tokens)


# --------------------------------------------------------------------------
# Data loading
# --------------------------------------------------------------------------
def load_training_data() -> Tuple[List[str], List[str], int, int]:
    """Return (texts, labels, malformed_count, total_count) from MongoDB."""
    db = get_db()
    docs = list(db["case_training_data_temp"].find({}))
    texts: List[str] = []
    labels: List[str] = []
    malformed = 0
    for d in docs:
        text = clean_text(d.get("text") or "")
        label = (d.get("category_id") or "").strip()
        if not text or not label:
            malformed += 1
            continue
        texts.append(text)
        labels.append(label)
    return texts, labels, malformed, len(docs)


def load_category_map() -> Dict[str, str]:
    """Map category_id -> category name from ``legal_categories_temp``."""
    db = get_db()
    mapping: Dict[str, str] = {}
    for c in db["legal_categories_temp"].find({}, {"category_id": 1, "name": 1, "_id": 0}):
        cid = (c.get("category_id") or "").strip()
        if cid:
            mapping[cid] = c.get("name") or cid
    return mapping


def load_category_defs() -> Dict[str, Dict[str, Any]]:
    """Map category_id -> {name, description, keywords} (canonical definitions)."""
    db = get_db()
    defs: Dict[str, Dict[str, Any]] = {}
    for c in db["legal_categories_temp"].find({}):
        cid = (c.get("category_id") or "").strip()
        if not cid:
            continue
        defs[cid] = {
            "name": c.get("name") or cid,
            "description": c.get("description") or "",
            "keywords": [k for k in (c.get("keywords") or []) if k],
        }
    return defs


def data_signature(
    texts: List[str], labels: List[str], cat_defs: Dict[str, Dict[str, Any]]
) -> str:
    """Deterministic hash of training data + category definitions + pipeline version."""
    h = hashlib.sha256()
    h.update(PIPELINE_VERSION.encode("utf-8"))
    for text, label in sorted(zip(texts, labels)):
        h.update(text.encode("utf-8", "ignore"))
        h.update(b"\x00")
        h.update(label.encode("utf-8", "ignore"))
        h.update(b"\x01")
    h.update(json.dumps(cat_defs, sort_keys=True).encode("utf-8"))
    return h.hexdigest()


# --------------------------------------------------------------------------
# Feature extraction
# --------------------------------------------------------------------------
def build_vectorizer() -> FeatureUnion:
    """Word unigrams+bigrams combined with character (char_wb) n-grams."""
    return FeatureUnion(
        [
            (
                "word",
                TfidfVectorizer(
                    ngram_range=(1, 2),
                    analyzer="word",
                    sublinear_tf=True,
                    min_df=1,
                    max_df=0.9,
                    lowercase=False,
                ),
            ),
            (
                "char",
                TfidfVectorizer(
                    ngram_range=(2, 4),
                    analyzer="char_wb",
                    sublinear_tf=True,
                    min_df=1,
                    max_df=0.9,
                    lowercase=False,
                ),
            ),
        ]
    )


def augment_dataset(
    texts: List[str], labels: List[str], cat_defs: Dict[str, Dict[str, Any]]
) -> Tuple[List[str], List[str]]:
    """Append canonical category definitions as labelled training documents.

    This injects the category's own vocabulary (name, description, and each
    keyword) into the model so short real-world input can match it. These are
    existing MongoDB definitions, not invented legal expertise.
    """
    aug_texts = list(texts)
    aug_labels = list(labels)
    for cid, d in cat_defs.items():
        combined = " ".join(
            [clean_text(d["name"]), clean_text(d["description"])]
            + [clean_text(k) for k in d["keywords"]]
        )
        aug_texts.append(combined)
        aug_labels.append(cid)
        for kw in d["keywords"]:
            aug_texts.append(clean_text(kw))
            aug_labels.append(cid)
    return aug_texts, aug_labels


def build_category_phrases(cat_defs: Dict[str, Dict[str, Any]]) -> Dict[str, set]:
    """Build a per-category set of canonical phrases for hybrid scoring.

    Uses the canonical ``keywords`` from the database plus the curated
    high-precision patterns. Category *names* are intentionally not used as
    single-token signals because words like "property" or "family" are too
    generic to be discriminative.
    """
    phrases: Dict[str, set] = {}
    for cid, d in cat_defs.items():
        s = {clean_text(k) for k in d["keywords"]}
        for p in _CURATED_PATTERNS.get(cid, []):
            s.add(clean_text(p))
        phrases[cid] = {p for p in s if p}
    return phrases


# --------------------------------------------------------------------------
# Training / caching
# --------------------------------------------------------------------------
_STATE: Dict[str, Any] = {}


def _cache_dir() -> Path:
    path = Path(settings.MODEL_CACHE_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _model_path() -> Path:
    return _cache_dir() / "model.pkl"


def _meta_path() -> Path:
    return _cache_dir() / "model_meta.json"


def _load_cached(signature: str) -> Optional[Dict[str, Any]]:
    if not _model_path().exists() or not _meta_path().exists():
        return None
    try:
        meta = json.loads(_meta_path().read_text(encoding="utf-8"))
        if meta.get("signature") != signature:
            return None
        with open(_model_path(), "rb") as fh:
            bundle = pickle.load(fh)
        _STATE["bundle"] = bundle
        _STATE["meta"] = meta
        return meta
    except Exception as exc:  # pragma: no cover - corrupt cache
        logger.warning("Discarding invalid cached model: %s", exc)
        return None


def train(force: bool = False) -> Dict[str, Any]:
    """Train (or reload) the hybrid classifier and return diagnostics."""
    texts, labels, malformed, total = load_training_data()
    if not texts:
        raise ClassificationError(
            "No usable labeled examples found in 'case_training_data_temp'. "
            "Import the training dataset before classifying cases."
        )

    cat_defs = load_category_defs()
    if not cat_defs:
        raise ClassificationError(
            "No legal categories found in 'legal_categories_temp'. "
            "Import the category dataset before classifying cases."
        )

    signature = data_signature(texts, labels, cat_defs)
    if not force:
        cached = _load_cached(signature)
        if cached is not None:
            return cached

    classes = sorted(set(labels))
    if len(classes) < 2:
        raise ClassificationError("Training data has fewer than two distinct categories.")

    aug_texts, aug_labels = augment_dataset(texts, labels, cat_defs)

    vectorizer = build_vectorizer()
    X = vectorizer.fit_transform(aug_texts)
    y = np.array([classes.index(l) for l in aug_labels])

    model = LogisticRegression(
        C=1.5, solver="lbfgs", max_iter=3000, random_state=42
    )
    model.fit(X, y)

    bundle = {
        "vectorizer": vectorizer,
        "model": model,
        "classes": classes,
        "category_map": {cid: cat_defs[cid]["name"] for cid in classes if cid in cat_defs},
        "phrases": build_category_phrases(cat_defs),
    }
    meta = {
        "signature": signature,
        "pipeline_version": PIPELINE_VERSION,
        "classes": classes,
        "category_map": bundle["category_map"],
        "malformed_examples": malformed,
        "original_examples": total,
        "augmented_examples": len(aug_texts),
        "metrics": {},  # populated by the evaluation CLI (evaluate_model.py)
    }

    try:
        with open(_model_path(), "wb") as fh:
            pickle.dump(bundle, fh, protocol=pickle.HIGHEST_PROTOCOL)
        _meta_path().write_text(json.dumps(meta, indent=2), encoding="utf-8")
    except OSError as exc:  # pragma: no cover
        logger.warning("Could not persist model cache: %s", exc)

    _STATE["bundle"] = bundle
    _STATE["meta"] = meta
    logger.info("Trained classifier (pipeline v%s) on %d documents.", PIPELINE_VERSION, len(aug_texts))
    return meta


def ensure_model() -> Dict[str, Any]:
    """Return the loaded model bundle, training if necessary."""
    if _STATE.get("bundle") is not None:
        return _STATE["bundle"]
    train(force=False)
    bundle = _STATE.get("bundle")
    if bundle is None:
        raise ClassificationError("Classifier failed to initialise.")
    return bundle


def model_diagnostics() -> Dict[str, Any]:
    """Human/API-readable snapshot of the classifier state."""
    meta = _STATE.get("meta")
    if meta is None and _meta_path().exists():
        try:
            meta = json.loads(_meta_path().read_text(encoding="utf-8"))
        except Exception:
            meta = None
    if meta is None:
        return {"ready": False, "message": "Model has not been trained yet."}
    return {
        "ready": True,
        "pipeline_version": meta.get("pipeline_version"),
        "signature": meta.get("signature"),
        "num_categories": len(meta.get("classes", [])),
        "categories": meta.get("classes", []),
        "malformed_examples": meta.get("malformed_examples"),
        "original_examples": meta.get("original_examples"),
        "augmented_examples": meta.get("augmented_examples"),
        "metrics": meta.get("metrics", {}),
    }


# --------------------------------------------------------------------------
# Prediction
# --------------------------------------------------------------------------
_STANDARD_EXPLANATION = (
    "This is an automated classification based on the text provided, intended "
    "to route your case to an appropriate lawyer. It is not legal advice. A "
    "lawyer should review the details of your matter before any decision is made."
)


def predict(text: str) -> Dict[str, Any]:
    """Classify a free-text legal description (hybrid model + keyword scoring).

    Returns ``category_id``, ``category_name``, a calibrated ``confidence``,
    a decision ``margin``, and a ``review_recommended`` flag when the result is
    too uncertain to present as definitive.
    """
    cleaned = clean_text(text)
    word_count = len(cleaned.split())
    if not cleaned or word_count < 2 or len(cleaned) < settings.MIN_DESCRIPTION_LENGTH:
        raise ClassificationError(
            "Please provide a longer description of your legal issue so it can "
            "be classified meaningfully."
        )

    bundle = ensure_model()
    vectorizer = bundle["vectorizer"]
    model = bundle["model"]
    classes: List[str] = bundle["classes"]
    category_map: Dict[str, str] = bundle["category_map"]
    phrases: Dict[str, set] = bundle["phrases"]

    X = vectorizer.transform([cleaned])
    proba = model.predict_proba(X)[0]
    proba_map = {cid: float(proba[i]) for i, cid in enumerate(classes)}

    # Hybrid keyword-overlap score.
    kw = {cid: 0.0 for cid in classes}
    for cid, ph in phrases.items():
        if cid not in kw:
            continue
        for p in ph:
            if p and p in cleaned:
                if p in _DOMINANT_PHRASES:
                    weight = 10.0
                elif p in _HIGH_WEIGHT_PHRASES:
                    weight = 3.0
                else:
                    weight = 1.0 + 0.5 * p.count(" ")
                kw[cid] += weight
    kw_total = sum(kw.values())
    if kw_total > 0:
        kw_norm = {cid: kw[cid] / kw_total for cid in classes}
    else:
        kw_norm = {cid: 1.0 / len(classes) for cid in classes}

    final = {
        cid: _MODEL_WEIGHT * proba_map[cid] + _KEYWORD_WEIGHT * kw_norm[cid]
        for cid in classes
    }
    best = max(final, key=final.get)
    sorted_final = sorted(final.values(), reverse=True)
    margin = round((sorted_final[0] - sorted_final[1]), 4) if len(sorted_final) > 1 else 1.0

    # Uncertain when the combined decision margin is too small to separate the
    # top category from the runner-up. A strong canonical keyword match yields a
    # large margin even when the raw model probability is low (which is exactly
    # the intended behaviour of the hybrid).
    review = margin < _REVIEW_MARGIN_THRESHOLD

    return {
        "category_id": best,
        "category_name": category_map.get(best, best),
        # Hybrid confidence: weighted model probability + canonical keyword match.
        # It is a decision confidence in [0, 1], not a guarantee of correctness.
        "confidence": round(final[best], 4),
        "margin": margin,
        "review_recommended": review,
        "explanation": _STANDARD_EXPLANATION,
        "word_count": word_count,
    }
