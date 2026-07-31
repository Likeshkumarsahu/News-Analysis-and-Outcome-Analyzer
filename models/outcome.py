import os
import joblib
import numpy as np

MODEL_PATH = "models/outcome_model/impact_classifier.joblib"

_pipeline = None


def _load_model():
    global _pipeline
    if _pipeline is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(
                f"Model not found at {MODEL_PATH}. "
                "Run: python notebooks/train_outcome_model.py"
            )
        _pipeline = joblib.load(MODEL_PATH)
        print("  Loaded ML impact classifier.")
    return _pipeline


def predict_outcome(text: str) -> dict:
    """
    Predict impact level using trained TF-IDF + Logistic Regression.

    Returns:
        {
            "impact":      "HIGH" | "MEDIUM" | "LOW",
            "confidence":  float,
            "matched":     list (top contributing words),
            "explanation": str
        }
    """
    try:
        model = _load_model()

        # Predict
        label      = model.predict([text])[0]
        proba      = model.predict_proba([text])[0]
        confidence = round(float(np.max(proba)), 3)

        # Extract top contributing words via TF-IDF weights
        vectorizer = model.named_steps["tfidf"]
        clf        = model.named_steps["clf"]
        features   = vectorizer.get_feature_names_out()

        # Get class index
        class_idx  = list(clf.classes_).index(label)

        # Transform text and get feature scores
        tfidf_vec  = vectorizer.transform([text]).toarray()[0]
        coef       = clf.coef_[class_idx]
        scores     = tfidf_vec * coef

        # Top positive contributing words
        top_idx    = np.argsort(scores)[-5:][::-1]
        top_words  = [
            features[i] for i in top_idx
            if scores[i] > 0 and features[i] in text.lower()
        ]

        explanation = (
            f"ML model predicts {label} impact "
            f"(confidence: {confidence:.0%}). "
            f"Key signals: {', '.join(top_words) if top_words else 'none detected'}."
        )

        return {
            "impact":      label,
            "confidence":  confidence,
            "matched":     top_words,
            "explanation": explanation,
        }

    except FileNotFoundError as e:
        # Fallback to rule-based if model not trained yet
        print(f"  ML model not found, using rule-based fallback: {e}")
        return _rule_based_fallback(text)


# ── Rule-based fallback ───────────────────────────────────────────────────────
# Used only if ML model hasn't been trained yet

_HIGH = [
    "war", "attack", "crisis", "collapse", "explosion", "disaster",
    "earthquake", "flood", "tsunami", "pandemic", "assassination",
    "nuclear", "sanctions", "recession", "crash", "protest", "coup",
    "strike", "riot", "emergency", "outbreak", "invasion", "conflict",
    "tension", "ceasefire", "airstrike", "missile", "border",
    "military", "troops", "shelling", "hostility", "backfired",
    "isolate", "killed", "dead", "blast", "bomb", "violence", "terror",
]
_MEDIUM = [
    "election", "policy", "reform", "agreement", "deal", "trade",
    "inflation", "unemployment", "growth", "summit", "treaty",
    "budget", "tax", "interest rate", "gdp", "deficit", "alliance",
    "regulation", "merger", "acquisition", "investigation",
]
_LOW = [
    "launch", "release", "announce", "award", "celebrate", "open",
    "upgrade", "update", "appoint", "promote", "partner", "expand",
    "report", "study", "survey", "publish", "event", "festival",
]


def _rule_based_fallback(text: str) -> dict:
    t = text.lower()
    h = [kw for kw in _HIGH   if kw in t]
    m = [kw for kw in _MEDIUM if kw in t]
    l = [kw for kw in _LOW    if kw in t]

    if h:
        return {"impact": "HIGH",   "confidence": min(0.6 + len(h)*0.1, 0.95), "matched": h, "explanation": f"Rule-based: {', '.join(h)}"}
    if m:
        return {"impact": "MEDIUM", "confidence": min(0.5 + len(m)*0.08, 0.85), "matched": m, "explanation": f"Rule-based: {', '.join(m)}"}
    return {"impact": "LOW", "confidence": 0.4, "matched": l, "explanation": "Rule-based: no strong signals."}