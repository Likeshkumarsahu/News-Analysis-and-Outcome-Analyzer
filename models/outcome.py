# Rule-based outcome predictor
# Replaces the custom-trained model which had no training data in the repo

HIGH_KEYWORDS = [
    "war", "attack", "crisis", "collapse", "explosion", "disaster",
    "earthquake", "flood", "tsunami", "pandemic", "assassination",
    "nuclear", "sanctions", "recession", "crash", "protest", "coup",
    "strike", "riot", "emergency", "outbreak", "invasion", "conflict",
    "tension", "ceasefire", "airstrike", "missile", "border",
    "military", "troops", "shelling", "hostility", "backfired",
    "isolate", "escalat", "retaliat", "standoff", "provocation",
]

MEDIUM_KEYWORDS = [
    "election", "policy", "reform", "agreement", "deal", "trade",
    "inflation", "unemployment", "growth", "summit", "treaty",
    "budget", "tax", "interest rate", "gdp", "deficit", "alliance",
    "regulation", "merger", "acquisition", "investigation",
]

LOW_KEYWORDS = [
    "launch", "release", "announce", "award", "celebrate", "open",
    "upgrade", "update", "appoint", "promote", "partner", "expand",
    "report", "study", "survey", "publish", "event", "festival",
]


def predict_outcome(text: str) -> dict:
    """
    Predict impact level of a news article.

    Returns:
        {
            "impact":      "HIGH" | "MEDIUM" | "LOW",
            "confidence":  float (0-1),
            "matched":     list of matched keywords,
            "explanation": str
        }
    """
    text_lower = text.lower()

    high_matches   = [kw for kw in HIGH_KEYWORDS   if kw in text_lower]
    medium_matches = [kw for kw in MEDIUM_KEYWORDS if kw in text_lower]
    low_matches    = [kw for kw in LOW_KEYWORDS    if kw in text_lower]

    h = len(high_matches)
    m = len(medium_matches)
    l = len(low_matches)
    total = h + m + l or 1   # avoid division by zero

    if h > 0:
        impact     = "HIGH"
        confidence = round(min(0.6 + (h * 0.1), 0.95), 2)
        matched    = high_matches
        explanation = f"Contains {h} high-impact signal(s): {', '.join(high_matches)}"

    elif m > 0:
        impact     = "MEDIUM"
        confidence = round(min(0.5 + (m * 0.08), 0.85), 2)
        matched    = medium_matches
        explanation = f"Contains {m} medium-impact signal(s): {', '.join(medium_matches)}"

    elif l > 0:
        impact     = "LOW"
        confidence = round(min(0.4 + (l * 0.06), 0.75), 2)
        matched    = low_matches
        explanation = f"Contains {l} low-impact signal(s): {', '.join(low_matches)}"

    else:
        impact     = "LOW"
        confidence = 0.4
        matched    = []
        explanation = "No strong impact signals detected."

    return {
        "impact":      impact,
        "confidence":  confidence,
        "matched":     matched,
        "explanation": explanation,
    }