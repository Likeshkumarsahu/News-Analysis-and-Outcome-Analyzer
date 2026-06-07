import os
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)

_pipeline_ready = False


def _ensure_pipeline():
    global _pipeline_ready
    if not _pipeline_ready:
        from embeddings.embed_store import get_collection
        get_collection()
        _pipeline_ready = True


# ── Pages ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


# ── Analyze ───────────────────────────────────────────────────────────────────

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

        results = search(query, top_k=5)
        if not results:
            return jsonify({"error": f"No relevant articles found for '{query}'."}), 404

        top_text  = results[0]["text"]
        sentiment = analyze_sentiment(top_text)
        outcome   = predict_outcome(top_text)

        explanation = explain(
            query=query,
            retrieved_articles=results,
            sentiment=sentiment,
            outcome=outcome,
        )

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
                    "score":     round(float(a["score"]), 3),
                    "text":      a["text"][:300],
                }
                for a in results[:5]
            ],
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Ingest ────────────────────────────────────────────────────────────────────

@app.route("/api/ingest", methods=["POST"])
def ingest():
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


# ── Status ────────────────────────────────────────────────────────────────────

@app.route("/api/status", methods=["GET"])
def status():
    try:
        from embeddings.embed_store import get_collection
        count = get_collection().count()
        return jsonify({"status": "ok", "articles_in_db": count})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ── XAI ───────────────────────────────────────────────────────────────────────

@app.route("/api/explain", methods=["POST"])
def xai_explain():
    data = request.get_json()
    if not data or not data.get("text", "").strip():
        return jsonify({"error": "text is required"}), 400
    try:
        from xai.lime_explainer import explain_full
        result = explain_full(data["text"])
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Evaluation ────────────────────────────────────────────────────────────────

@app.route("/api/evaluate", methods=["POST"])
def evaluate_pipeline():
    try:
        from evaluation.ragas_eval import run_evaluation
        scores = run_evaluation()
        return jsonify({"scores": scores})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Knowledge Graph ───────────────────────────────────────────────────────────

@app.route("/api/graph", methods=["GET"])
def get_graph():
    try:
        from knowledge_graph.graph_builder import load_graph
        graph = load_graph()
        return jsonify(graph)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/graph/rebuild", methods=["POST"])
def rebuild_graph():
    try:
        from knowledge_graph.graph_builder import build_graph
        graph = build_graph()
        return jsonify({
            "message": f"Graph rebuilt: {len(graph['nodes'])} nodes, {len(graph['links'])} edges"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)