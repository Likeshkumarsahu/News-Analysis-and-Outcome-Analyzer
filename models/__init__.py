# Intentionally minimal — do NOT re-export analyze_sentiment/predict_outcome/
# explain from here. Those pull in heavyweight ML pipelines (RoBERTa via
# transformers, a joblib model, LangGraph) at IMPORT TIME. Every consumer in
# this codebase already imports them directly from their own submodule
# (e.g. `from models.sentiment import analyze_sentiment`), so re-exporting
# them here only forces anything doing `import models.<anything>` — like the
# lightweight Article schema below — to pay for loading all three heavy
# pipelines it doesn't need. Keep this file light.
from .news_schema import Article, make_article_id