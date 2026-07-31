import os
import json
import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.pipeline import Pipeline

# ── Load processed articles ───────────────────────────────────────────────────
PROCESSED_PATH = "data/processed_news.json"
MODEL_PATH     = "models/outcome_model/impact_classifier.joblib"

os.makedirs("models/outcome_model", exist_ok=True)

with open(PROCESSED_PATH, "r") as f:
    articles = json.load(f)

print(f"Loaded {len(articles)} articles.")

# ── Auto-label using keyword system (weak supervision) ────────────────────────
HIGH_KEYWORDS = [
    "war", "attack", "crisis", "collapse", "explosion", "disaster",
    "earthquake", "flood", "tsunami", "pandemic", "assassination",
    "nuclear", "sanctions", "recession", "crash", "protest", "coup",
    "strike", "riot", "emergency", "outbreak", "invasion", "conflict",
    "tension", "ceasefire", "airstrike", "missile", "border",
    "military", "troops", "shelling", "hostility", "backfired",
    "isolate", "escalat", "retaliat", "standoff", "killed", "dead",
    "attack", "blast", "bomb", "violence", "terror", "war",
]

MEDIUM_KEYWORDS = [
    "election", "policy", "reform", "agreement", "deal", "trade",
    "inflation", "unemployment", "growth", "summit", "treaty",
    "budget", "tax", "interest rate", "gdp", "deficit", "alliance",
    "regulation", "merger", "acquisition", "investigation", "arrest",
    "verdict", "ruling", "court", "parliament", "minister", "vote",
]

LOW_KEYWORDS = [
    "launch", "release", "announce", "award", "celebrate", "open",
    "upgrade", "update", "appoint", "promote", "partner", "expand",
    "report", "study", "survey", "publish", "event", "festival",
    "review", "preview", "interview", "feature", "profile",
]


def auto_label(text: str) -> str:
    text_lower = text.lower()
    h = sum(1 for kw in HIGH_KEYWORDS   if kw in text_lower)
    m = sum(1 for kw in MEDIUM_KEYWORDS if kw in text_lower)
    l = sum(1 for kw in LOW_KEYWORDS    if kw in text_lower)
    if h > 0:   return "HIGH"
    if m > 0:   return "MEDIUM"
    return "LOW"


texts  = [a["full_text"] for a in articles if a.get("full_text")]
labels = [auto_label(t) for t in texts]

# Check label distribution
from collections import Counter
dist = Counter(labels)
print(f"Label distribution: {dict(dist)}")

# ── Train/test split ──────────────────────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    texts, labels,
    test_size=0.2,
    random_state=42,
    stratify=labels,
)

print(f"Train: {len(X_train)} | Test: {len(X_test)}")

# ── Build pipeline ────────────────────────────────────────────────────────────
pipeline = Pipeline([
    ("tfidf", TfidfVectorizer(
        max_features=5000,
        ngram_range=(1, 2),      # unigrams + bigrams
        sublinear_tf=True,       # log normalization
        min_df=2,                # ignore very rare terms
        stop_words="english",
    )),
    ("clf", LogisticRegression(
        max_iter=1000,
        class_weight="balanced", # handle class imbalance
        C=1.0,
        solver="lbfgs"
        # multi_class="multinomial",
    )),
])

# ── Train ─────────────────────────────────────────────────────────────────────
print("\nTraining...")
pipeline.fit(X_train, y_train)

# ── Evaluate ──────────────────────────────────────────────────────────────────
y_pred = pipeline.predict(X_test)

print("\n── Classification Report ──")
print(classification_report(y_test, y_pred))

print("── Confusion Matrix ──")
print(confusion_matrix(y_test, y_pred, labels=["LOW", "MEDIUM", "HIGH"]))

# ── Save model ────────────────────────────────────────────────────────────────
joblib.dump(pipeline, MODEL_PATH)
print(f"\nModel saved to {MODEL_PATH}")

# ── Show top features per class ───────────────────────────────────────────────
print("\n── Top 10 features per class ──")
vectorizer = pipeline.named_steps["tfidf"]
clf        = pipeline.named_steps["clf"]
features   = vectorizer.get_feature_names_out()

for i, class_name in enumerate(clf.classes_):
    top_idx = np.argsort(clf.coef_[i])[-10:][::-1]
    top_features = [features[j] for j in top_idx]
    print(f"  {class_name}: {', '.join(top_features)}")