"""Evaluate the legal-case classifier honestly.

* Compares a baseline (word TF-IDF + LogisticRegression, no augmentation) with
  the improved pipeline (word+char TF-IDF, category-definition augmentation,
  hybrid keyword scoring).
* Uses StratifiedGroupKFold with near-duplicate grouping so the templated
  training data cannot leak between train/validation folds.
* Runs a regression suite of natural-language examples (property-heavy) that is
  separate from the training data.

Usage (from ``backend``, virtualenv active):  python evaluate_model.py
"""
from __future__ import annotations

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import StratifiedGroupKFold

from app.database import close, connect
from app.services import classification
from app.services.classification import _DOMINANT_PHRASES, _HIGH_WEIGHT_PHRASES

# Hybrid combination weights (mirror classification.py).
_MODEL_WEIGHT = 0.6
_KEYWORD_WEIGHT = 0.4

# Known boilerplate lead-ins used by the synthetic dataset, so near-duplicate
# examples can be grouped for leakage-free evaluation.
_TEMPLATE_PREFIXES = [
    "please help me with this legal issue",
    "i am looking for a lawyer because",
    "my situation is that",
    "i need legal assistance regarding this matter",
    "can you classify this case",
    "the problem i want advice on is",
    "i would like to know my legal rights because",
    "i need to discuss the following issue with a lawyer",
    "this matter concerns the following",
    "i want to take legal action or understand my options because",
]


def _core(text: str) -> str:
    t = text.strip()
    for p in _TEMPLATE_PREFIXES:
        if t.startswith(p):
            return t[len(p):].strip()
    return t


def _hybrid_predict(proba_map, phrases, cleaned, classes):
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
    return max(final, key=final.get)


def _metrics(y_true, y_pred):
    return {
        "accuracy": round(accuracy_score(y_true, y_pred), 4),
        "macro_precision": round(precision_score(y_true, y_pred, average="macro", zero_division=0), 4),
        "macro_recall": round(recall_score(y_true, y_pred, average="macro", zero_division=0), 4),
        "macro_f1": round(f1_score(y_true, y_pred, average="macro", zero_division=0), 4),
    }


def _cv_evaluate(texts, labels, groups, classes, improved, cat_defs, phrases):
    skf = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
    y_true_all, y_pred_all = [], []
    for train_idx, test_idx in skf.split(texts, labels, groups):
        tr_texts = [texts[i] for i in train_idx]
        tr_labels = [labels[i] for i in train_idx]
        te_texts = [texts[i] for i in test_idx]
        te_labels = [labels[i] for i in test_idx]

        if improved:
            tr_texts, tr_labels = classification.augment_dataset(tr_texts, tr_labels, cat_defs)
            vec = classification.build_vectorizer()
        else:
            vec = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=1, max_df=0.9)

        Xtr = vec.fit_transform(tr_texts)
        Xte = vec.transform(te_texts)
        ytr = np.array([classes.index(l) for l in tr_labels])

        model = LogisticRegression(C=1.5, solver="lbfgs", max_iter=3000, random_state=42)
        model.fit(Xtr, ytr)
        proba = model.predict_proba(Xte)

        for i, true_label in enumerate(te_labels):
            proba_map = {cid: float(proba[i][classes.index(cid)]) for cid in classes}
            if improved:
                pred = _hybrid_predict(proba_map, phrases, te_texts[i], classes)
            else:
                pred = classes[int(np.argmax(proba[i]))]
            y_pred_all.append(pred)
            y_true_all.append(true_label)

    return _metrics(y_true_all, y_pred_all)


# Regression suite (separate from training data). Expected labels are the
# canonical category IDs from legal_categories_temp.
REGRESSION = [
    # --- property-related (the focus) ---
    ("My neighbour is claiming ownership of a portion of my land.", "PRO01"),
    ("My landlord refuses to return my rental security deposit.", "PRO02"),
    ("There is a dispute over the legal ownership of inherited property.", "PRO03"),
    ("A contractor failed to complete the agreed renovation work.", "CON01"),
    ("Someone forged property documents to claim ownership of my house.", "FRA01"),
    ("A person threatened to assault me during a property boundary dispute.", "CRI01"),
    ("My apartment purchase agreement was breached by the seller.", "CON01"),
    ("I paid for a property, but the seller refuses to transfer ownership.", "PRO01"),
    # --- every other category ---
    ("My bank has charged me unfair fees and interest on my loan.", "BANK01"),
    ("Someone owes me money and is refusing to repay the debt.", "CIV01"),
    ("The directors of my company are fighting over control of the business.", "COM01"),
    ("I want to register a new private limited company and need help with the paperwork.", "COM02"),
    ("The vendor breached our signed agreement and refuses to deliver.", "CON01"),
    ("I bought a defective product and the seller will not give a refund.", "CON02"),
    ("I have been accused of a criminal offence and need defence advice.", "CRI01"),
    ("I was tricked into sending money to an online scammer.", "CYB01"),
    ("My university rejected my exam grievance without explanation.", "EDU01"),
    ("I was fired from my job without notice and want to challenge it.", "EMP01"),
    ("My employer has not paid my salary for three months.", "EMP02"),
    ("A factory near my home is dumping waste and causing pollution.", "ENV01"),
    ("My spouse and I have a serious disagreement about our marriage.", "FAM01"),
    ("I want to file for divorce and need to understand the process.", "FAM02"),
    ("My ex-partner and I disagree about child custody.", "FAM03"),
    ("My spouse stopped paying maintenance and I need financial support.", "FAM04"),
    ("I was deceived into paying for a service with false information.", "FRA01"),
    ("My visa application was refused and I want to appeal.", "IMM01"),
    ("My insurance company rejected my claim without a valid reason.", "INS01"),
    ("Another company is using my trademark without permission.", "IPR01"),
    ("A hospital made a mistake during my surgery and I want to sue.", "MED01"),
    ("My landlord is trying to evict me without notice.", "PRO02"),
    ("My siblings are fighting over our father's will and estate.", "PRO03"),
    ("I received an income tax notice and need help responding.", "TAX01"),
    # --- overlapping / ambiguous ---
    ("My employer is harassing me at work and I fear for my safety.", "EMP01"),
    ("Someone is threatening me and demanding money.", "CRI01"),
    ("I lost my job and my employer will not pay my final settlement.", "EMP02"),
]


def main() -> int:
    connect()
    texts, labels, malformed, total = classification.load_training_data()
    cat_defs = classification.load_category_defs()
    classes = sorted(set(labels))
    groups = [_core(t) for t in texts]

    print(f"Data: {total} examples, {malformed} malformed, {len(classes)} categories")
    print(f"Unique core phrasings (near-duplicate groups): {len(set(groups))}")

    print("\n=== Cross-validation (StratifiedGroupKFold, dedup-aware) ===")
    base = _cv_evaluate(texts, labels, groups, classes, improved=False, cat_defs=None, phrases=None)
    print("BASELINE  (word TF-IDF + LR):", base)
    phrases = classification.build_category_phrases(cat_defs)
    impr = _cv_evaluate(texts, labels, groups, classes, improved=True, cat_defs=cat_defs, phrases=phrases)
    print("IMPROVED  (word+char + aug + hybrid):", impr)

    # Regression suite with the improved pipeline, fit on ALL data.
    print("\n=== Regression suite (improved pipeline) ===")
    aug_texts, aug_labels = classification.augment_dataset(texts, labels, cat_defs)
    vec = classification.build_vectorizer()
    X = vec.fit_transform(aug_texts)
    y = np.array([classes.index(l) for l in aug_labels])
    model = LogisticRegression(C=1.5, solver="lbfgs", max_iter=3000, random_state=42)
    model.fit(X, y)

    correct = 0
    for text, expected in REGRESSION:
        cleaned = classification.clean_text(text)
        px = vec.transform([cleaned])
        proba = model.predict_proba(px)[0]
        proba_map = {cid: float(proba[classes.index(cid)]) for cid in classes}
        pred = _hybrid_predict(proba_map, phrases, cleaned, classes)
        ok = pred == expected
        correct += int(ok)
        print(f"  [{'OK ' if ok else 'FAIL'}] {text[:60]:60s} exp={expected:6s} got={pred:6s} conf={proba_map[pred]*100:5.1f}%")

    print(f"\nRegression accuracy: {correct}/{len(REGRESSION)} = {correct/len(REGRESSION):.1%}")

    close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
