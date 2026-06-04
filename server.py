from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import xai
from xai.lime_explainer import explain_full
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)

# ── Lazy load pipeline modules ────────────────────────────────────────────────
# Imported here so Flask starts fast, models load on first request
_pipeline_ready = False

def _ensure_pipeline():
    global _pipeline_ready
    if not _pipeline_ready:
        from embeddings.embed_store import get_collection
        get_collection()   # warms up ChromaDB + BM25 index
        _pipeline_ready = True


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    if not data or not data.get("query", "").strip():
        return jsonify({"error": "Query is required"}), 400

    query = data["query"].strip()

    try:
        _ensure_pipeline()

        from retrieval.search       import search
        from models.sentiment       import analyze_sentiment
        from models.outcome         import predict_outcome
        from models.llm_explainer   import explain
        from xai.lime_explainer     import explain_full

        # Step 1: Retrieve
        results = search(query, top_k=5)
        if not results:
            return jsonify({"error": "No relevant articles found."}), 404

        # Step 2: top_text MUST be defined before anything uses it
        top_text  = results[0]["text"]

        # Step 3: Sentiment + Outcome
        sentiment = analyze_sentiment(top_text)
        outcome   = predict_outcome(top_text)

        # Step 4: LLM explanation
        explanation = explain(
            query=query,
            retrieved_articles=results,
            sentiment=sentiment,
            outcome=outcome,
        )

        # Step 5: XAI
        xai = explain_full(top_text)

        return jsonify({
            "query": query,
            "sentiment": {
                "label":      sentiment["label"],
                "confidence": sentiment["confidence"],
            },
            "outcome": {
                "impact":      outcome["impact"],
                "confidence":  outcome["confidence"],
                "matched":     outcome["matched"],
                "explanation": outcome["explanation"],
            },
            "explanation": explanation,
            "xai": {
                "sentiment": xai["sentiment_xai"],
                "outcome":   xai["outcome_xai"],
            },
            "articles": [
                {
                    "title":     a["title"],
                    "source":    a["source"],
                    "link":      a["link"],
                    "published": a["published"],
                    "score":     round(a["score"], 3),
                    "text":      a["text"][:300],
                }
                for a in results[:5]
            ],
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/explain", methods=["POST"])
def xai_explain():
    """
    POST /api/explain
    Body: { "text": "news text to explain" }
    Returns LIME word-level explanations for sentiment + outcome.
    """
    data = request.get_json()
    if not data or not data.get("text", "").strip():
        return jsonify({"error": "text is required"}), 400

    try:
        from xai.lime_explainer import explain_full
        result = explain_full(data["text"])
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.route("/api/ingest", methods=["POST"])
def ingest():
    """
    POST /api/ingest
    Triggers fresh news ingestion pipeline.
    """
    try:
        from ingestion.news_fetcher   import fetch_news, save_news
        from preprocessing.preprocess import process_news
        from embeddings.embed_store   import store_embeddings

        news = fetch_news()
        save_news(news)
        process_news()
        store_embeddings()

        return jsonify({"message": f"Ingestion complete. {len(news)} new articles added."})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/status", methods=["GET"])
def status():
    """GET /api/status — returns DB article count."""
    try:
        from embeddings.embed_store import get_collection
        count = get_collection().count()
        return jsonify({"status": "ok", "articles_in_db": count})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/evaluate", methods=["POST"])
def evaluate_pipeline():
    """
    POST /api/evaluate
    Runs RAGAS evaluation and returns scores.
    Warning: takes 1-2 minutes — calls LLM for each eval query.
    """
    try:
        from evaluation.ragas_eval import run_evaluation
        scores = run_evaluation()
        return jsonify({"scores": scores})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
