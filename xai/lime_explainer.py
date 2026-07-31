import os
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import numpy as np
from lime.lime_text import LimeTextExplainer
from models.sentiment import analyze_sentiment
from models.outcome import predict_outcome


# ── Explainer instances (created once) ───────────────────────────────────────
_sentiment_explainer = LimeTextExplainer(
    class_names=["NEGATIVE", "NEUTRAL", "POSITIVE"],
    feature_selection="auto",
)

_outcome_explainer = LimeTextExplainer(
    class_names=["LOW", "MEDIUM", "HIGH"],
    feature_selection="auto",
)


# ── Prediction functions for LIME ─────────────────────────────────────────────

def _sentiment_predict(texts: list[str]) -> np.ndarray:
    """
    Wrapper so LIME can call RoBERTa in batch.
    Returns array of shape (n_samples, 3) — [neg, neu, pos] probabilities.
    """
    results = []
    for text in texts:
        out = analyze_sentiment(text)
        label = out["label"].upper()
        conf  = out["confidence"]

        # Distribute confidence to the predicted label, rest split equally
        probs = [0.0, 0.0, 0.0]   # [NEG, NEU, POS]
        label_idx = {"NEGATIVE": 0, "NEUTRAL": 1, "POSITIVE": 2}.get(label, 1)
        remainder = (1.0 - conf) / 2
        for i in range(3):
            probs[i] = conf if i == label_idx else remainder

        results.append(probs)
    return np.array(results)


def _outcome_predict(texts: list[str]) -> np.ndarray:
    """
    Wrapper so LIME can call outcome predictor in batch.
    Returns array of shape (n_samples, 3) — [low, medium, high] probabilities.
    """
    results = []
    for text in texts:
        out = predict_outcome(text)
        label = out["impact"].upper()
        conf  = out["confidence"]

        probs = [0.0, 0.0, 0.0]   # [LOW, MED, HIGH]
        label_idx = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}.get(label, 0)
        remainder = (1.0 - conf) / 2
        for i in range(3):
            probs[i] = conf if i == label_idx else remainder

        results.append(probs)
    return np.array(results)


# ── Main XAI functions ────────────────────────────────────────────────────────

def explain_sentiment(text: str, num_features: int = 8) -> dict:
    """
    Run LIME on sentiment model.

    Returns:
        {
            "label":        predicted sentiment label,
            "confidence":   float,
            "top_words":    [ {"word": str, "weight": float, "direction": "supports"|"opposes"} ],
            "explanation":  human readable string
        }
    """
    sentiment = analyze_sentiment(text)
    label     = sentiment["label"].upper()
    label_idx = {"NEGATIVE": 0, "NEUTRAL": 1, "POSITIVE": 2}.get(label, 1)

    exp = _sentiment_explainer.explain_instance(
        text,
        _sentiment_predict,
        num_features=num_features,
        num_samples=100,     # low for CPU speed — increase to 300 for accuracy
        labels=[label_idx],
    )

    word_weights = exp.as_list(label=label_idx)

    top_words = []
    for word, weight in word_weights:
        top_words.append({
            "word":      word,
            "weight":    round(float(weight), 4),
            "direction": "supports" if weight > 0 else "opposes",
        })

    # Sort by absolute weight
    top_words.sort(key=lambda x: abs(x["weight"]), reverse=True)

    # Human readable
    supporting = [w["word"] for w in top_words if w["direction"] == "supports"][:3]
    opposing   = [w["word"] for w in top_words if w["direction"] == "opposes"][:3]

    explanation = f"Sentiment is {label} mainly because of: {', '.join(supporting) or 'no strong signals'}."
    if opposing:
        explanation += f" Words pulling against this: {', '.join(opposing)}."

    return {
        "label":       label,
        "confidence":  sentiment["confidence"],
        "top_words":   top_words,
        "explanation": explanation,
    }


def explain_outcome(text: str, num_features: int = 8) -> dict:
    """
    Run LIME on outcome/impact model.

    Returns:
        {
            "impact":       predicted impact label,
            "confidence":   float,
            "top_words":    [ {"word": str, "weight": float, "direction": "supports"|"opposes"} ],
            "explanation":  human readable string
        }
    """
    outcome   = predict_outcome(text)
    label     = outcome["impact"].upper()
    label_idx = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}.get(label, 0)

    exp = _outcome_explainer.explain_instance(
        text,
        _outcome_predict,
        num_features=num_features,
        num_samples=100,
        labels=[label_idx],
    )

    word_weights = exp.as_list(label=label_idx)

    top_words = []
    for word, weight in word_weights:
        top_words.append({
            "word":      word,
            "weight":    round(float(weight), 4),
            "direction": "supports" if weight > 0 else "opposes",
        })

    top_words.sort(key=lambda x: abs(x["weight"]), reverse=True)

    supporting = [w["word"] for w in top_words if w["direction"] == "supports"][:3]
    opposing   = [w["word"] for w in top_words if w["direction"] == "opposes"][:3]

    explanation = f"Impact is {label} mainly because of: {', '.join(supporting) or 'no strong signals'}."
    if opposing:
        explanation += f" Words reducing impact score: {', '.join(opposing)}."

    return {
        "impact":      label,
        "confidence":  outcome["confidence"],
        "top_words":   top_words,
        "explanation": explanation,
    }


def explain_full(text: str) -> dict:
    """
    Run both sentiment and outcome LIME explanations.
    Returns combined dict — used by server.py /api/explain endpoint.
    """
    return {
        "sentiment_xai": explain_sentiment(text),
        "outcome_xai":   explain_outcome(text),
    }