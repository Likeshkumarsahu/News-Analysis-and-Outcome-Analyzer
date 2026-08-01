import os
os.environ["TRANSFORMERS_OFFLINE"] = "0"
os.environ["HF_DATASETS_OFFLINE"] = "0"
os.environ["HF_HUB_OFFLINE"] = "0"

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

    query      = data["query"].strip()
    provider   = data.get("provider", "local")     # local | anthropic | openai | gemini | groq
    llm_model  = data.get("llm_model")
    api_key    = data.get("api_key")

    try:
        from cache.redis_cache import get_cached, set_cached
        cache_key_extra = f"{provider}:{llm_model}"

        cached = get_cached(query, provider, llm_model)
        if cached:
            cached["_cached"] = True
            return jsonify(cached)

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

        llm_result = explain(
            query=query, retrieved_articles=results, sentiment=sentiment,
            outcome=outcome, provider=provider, llm_model=llm_model, api_key=api_key,
        )

        if llm_result["hitl_required"]:
            return jsonify({"hitl_required": True, "message": llm_result["text"]}), 202

        xai = explain_full(top_text)

        result = {
            "query": query,
            "provider": provider,
            "sentiment": {"label": sentiment["label"], "confidence": sentiment["confidence"]},
            "outcome": {
                "impact": outcome["impact"], "confidence": outcome["confidence"],
                "matched": outcome["matched"], "explanation": outcome["explanation"],
            },
            "explanation": llm_result["text"],
            "llm_meta": {
                "provider_used": llm_result["provider_used"],
                "model_used":    llm_result["model_used"],
                "cost_usd":      llm_result["cost_usd"],
                "latency_ms":    llm_result["latency_ms"],
                "fallback_hops": llm_result.get("fallback_hops", 0),
                "pii_redacted":  llm_result.get("pii_redacted", []),
            },
            "xai": {"sentiment": xai["sentiment_xai"], "outcome": xai["outcome_xai"]},
            "articles": [
                {"title": a["title"], "source": a["source"], "link": a["link"],
                 "published": a["published"], "score": round(float(a["score"]), 3),
                 "text": a["text"][:300]}
                for a in results[:5]
            ],
            "_cached": False,
        }

        if not llm_result["blocked"] and "unavailable" not in llm_result["text"].lower():
            set_cached(query, provider, result, llm_model)

        return jsonify(result)

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

# ── LLM Status ───────────────────────────────────────────────────────────────

@app.route("/api/llm/status", methods=["GET"])
def llm_status():
    """Check local Ollama connectivity for the frontend toggle."""
    try:
        from models.llm_explainer import check_ollama_connected, GROQ_FREE_MODELS
        status = check_ollama_connected()
        status["groq_models"] = GROQ_FREE_MODELS
        return jsonify(status)
    except Exception as e:
        return jsonify({"connected": False, "model_available": False, "message": str(e)}), 500


@app.route("/api/cache/status", methods=["GET"])
def cache_status_route():
    from cache.redis_cache import cache_status
    return jsonify(cache_status())


@app.route("/api/cache/clear", methods=["POST"])
def cache_clear_route():
    from cache.redis_cache import clear_cache
    count = clear_cache()
    return jsonify({"message": f"Cleared {count} cached entries."})

# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)

@app.route("/api/crew", methods=["POST"])
def crew_analyze():
    """
    POST /api/crew
    Body: { "query": "your query" }
    Runs full multi-agent CrewAI pipeline.
    Warning: takes 3-5 minutes — 3 agents, multiple LLM calls.
    """
    data = request.get_json()
    if not data or not data.get("query", "").strip():
        return jsonify({"error": "Query is required"}), 400

    query = data["query"].strip()

    try:
        from agents.news_crew import run_news_crew
        result = run_news_crew(query)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/pii/scan", methods=["POST"])
def pii_scan():
    data = request.get_json()
    text = data.get("text", "")
    try:
        from guardrails.pii import scan_pii
        return jsonify({"entities": scan_pii(text)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500