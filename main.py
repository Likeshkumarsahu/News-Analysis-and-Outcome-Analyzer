import os
import sys
from dotenv import load_dotenv

load_dotenv()

os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"

# ── Pipeline imports ──────────────────────────────────────────────────────────
from ingestion.news_fetcher     import fetch_news, save_news
from preprocessing.preprocess   import process_news
from embeddings.embed_store     import store_embeddings
from retrieval.search           import search
from models.sentiment           import analyze_sentiment
from models.outcome             import predict_outcome
from models.llm_explainer       import explain


def run_pipeline():
    """
    Full ingestion pipeline — fetch → preprocess → embed.
    Run once at startup to ensure DB is populated.
    """
    print("\n" + "="*50)
    print("  STEP 1: Fetching news")
    print("="*50)
    news = fetch_news()
    save_news(news)

    print("\n" + "="*50)
    print("  STEP 2: Preprocessing")
    print("="*50)
    process_news()

    print("\n" + "="*50)
    print("  STEP 3: Storing embeddings")
    print("="*50)
    store_embeddings()

    print("\n✅ Pipeline complete.\n")


def analyze_query(query: str) -> dict:
    """
    Run full analysis on a user query.

    Steps:
        1. Hybrid retrieval (BM25 + semantic + CrossEncoder)
        2. Sentiment analysis on top result
        3. Outcome/impact prediction on top result
        4. LLM explanation using all context

    Returns dict with all results.
    """
    print(f"\n🔍 Searching for: '{query}'")

    # ── Step 1: Retrieve ──────────────────────────────────────────────────────
    results = search(query, top_k=5)

    if not results:
        return {
            "query":     query,
            "error":     "No relevant articles found. Try a different query.",
            "retrieved": [],
        }

    print(f"  Retrieved {len(results)} articles.")

    # ── Step 2: Sentiment ─────────────────────────────────────────────────────
    top_text  = results[0]["text"]
    sentiment = analyze_sentiment(top_text)
    print(f"  Sentiment: {sentiment['label']} ({sentiment['confidence']})")

    # ── Step 3: Outcome ───────────────────────────────────────────────────────
    outcome = predict_outcome(top_text)
    print(f"  Impact: {outcome['impact']} ({outcome['confidence']})")

    # ── Step 4: LLM explanation ───────────────────────────────────────────────
    print("  Generating explanation...")
    explanation = explain(
        query=query,
        retrieved_articles=results,
        sentiment=sentiment,
        outcome=outcome,
    )

    return {
        "query":       query,
        "retrieved":   results,
        "sentiment":   sentiment,
        "outcome":     outcome,
        "explanation": explanation,
    }


def print_result(result: dict):
    """Pretty print analysis result to terminal."""

    if "error" in result:
        print(f"\n❌ {result['error']}")
        return

    print("\n" + "="*50)
    print(f"  QUERY: {result['query']}")
    print("="*50)

    print(f"\n📰 TOP ARTICLES RETRIEVED:")
    for i, art in enumerate(result["retrieved"][:3], 1):
        print(f"  {i}. [{art['source']}] {art['title']}")
        print(f"     Score: {art['score']:.3f} | {art['link']}")

    print(f"\n📊 SENTIMENT:  {result['sentiment']['label']} "
          f"(confidence: {result['sentiment']['confidence']})")

    print(f"\n⚡ IMPACT:     {result['outcome']['impact']} "
          f"(confidence: {result['outcome']['confidence']})")
    if result["outcome"]["matched"]:
        print(f"   Signals:   {', '.join(result['outcome']['matched'])}")

    print(f"\n🤖 EXPLANATION:\n")
    print(f"   {result['explanation']}")
    print("\n" + "="*50)


def interactive_loop():
    """CLI query loop — keeps running until user types 'exit'."""

    print("\n" + "="*50)
    print("  NEWS ANALYSIS & OUTCOME ANALYZER")
    print("  Type your query. Type 'exit' to quit.")
    print("="*50)

    while True:
        try:
            query = input("\n> Query: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nExiting...")
            sys.exit(0)

        if not query:
            continue

        if query.lower() in ("exit", "quit", "q"):
            print("Bye!")
            sys.exit(0)

        result = analyze_query(query)
        print_result(result)


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":

    # Parse simple CLI args
    # python main.py --skip-ingest   → skip pipeline, go straight to query loop
    # python main.py --query "..."   → single query, no interactive loop

    skip_ingest  = "--skip-ingest" in sys.argv
    single_query = None

    if "--query" in sys.argv:
        idx = sys.argv.index("--query")
        if idx + 1 < len(sys.argv):
            single_query = sys.argv[idx + 1]

    # Run ingestion pipeline unless skipped
    if not skip_ingest:
        run_pipeline()
    else:
        print("\n⚡ Skipping ingestion (--skip-ingest flag set)")
        # Still need to init embeddings module so BM25 index builds
        from embeddings.embed_store import get_collection
        get_collection()

    # Single query mode or interactive loop
    if single_query:
        result = analyze_query(single_query)
        print_result(result)
    else:
        interactive_loop()