from transformers import pipeline
import torch

import os
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"

# Load once at module level
print("  Loading RoBERTa sentiment model...")

_sentiment_pipeline = pipeline(
    "sentiment-analysis",
    model="cardiffnlp/twitter-roberta-base-sentiment-latest",
    device=0 if torch.cuda.is_available() else -1,  # CPU fallback
    truncation=True,
    max_length=512,
)

# Label map — this model returns LABEL_0/1/2
_LABEL_MAP = {
    "LABEL_0": "NEGATIVE",
    "LABEL_1": "NEUTRAL",
    "LABEL_2": "POSITIVE",
}


def analyze_sentiment(text: str) -> dict:
    """
    Run RoBERTa sentiment on text.

    Returns:
        {
            "label":      "POSITIVE" | "NEGATIVE" | "NEUTRAL",
            "confidence": float (0-1),
            "raw_label":  str  (original model label)
        }
    """
    if not text or not text.strip():
        return {"label": "NEUTRAL", "confidence": 0.0, "raw_label": "LABEL_1"}

    try:
        result = _sentiment_pipeline(text[:512])[0]  # hard cap at 512 tokens
        raw    = result["label"]
        label  = _LABEL_MAP.get(raw, raw)            # normalize label

        return {
            "label":      label,
            "confidence": round(result["score"], 3),
            "raw_label":  raw,
        }

    except Exception as e:
        print(f"  Sentiment error: {e}")
        return {"label": "NEUTRAL", "confidence": 0.0, "raw_label": "error"}