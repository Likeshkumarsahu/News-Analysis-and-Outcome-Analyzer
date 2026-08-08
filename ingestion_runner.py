"""
ingestion_runner.py
=====================
Orchestrates the full ingestion pipeline:
  1. RSS feeds (existing, synchronous)               -> data/raw_news.json
  2. GDELT + NewsAPI (async, run concurrently)        -> data/raw/ per-run
     dump, deduplicated against RSS and each other, then merged into
     data/raw_news.json so preprocessing/embeddings run unchanged.
  3. Preprocessing (SpaCy NER + cleaning)             -> data/processed_news.json
  4. Vector DB embedding (ChromaDB)

Configure via env vars (.env):
  INGEST_QUERIES        comma-separated search queries for GDELT/NewsAPI
                         (default: "India,world news")
  INGEST_LOOKBACK_DAYS  how many days back to fetch (default: 2)
  NEWS_API_KEY          required to enable NewsAPI — GDELT still runs
                         without it, NewsAPI is just skipped with a warning

Run: uv run ingestion_runner.py   (or) python ingestion_runner.py
"""

import asyncio
import json
import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

from ingestion.news_fetcher import fetch_news, save_news
from ingestion.gdelt_connector import GDELTConnector
from ingestion.newsapi_connector import NewsAPIConnector, NewsAPIAuthError
from preprocessing.preprocess import process_news
from embeddings.embed_store import store_embeddings

load_dotenv()

RAW_DIR = "data/raw"
DEFAULT_QUERIES = ["India", "world news"]


def _load_existing_ids() -> set:
    """IDs already in data/raw_news.json — used for cross-source dedup."""
    path = "data/raw_news.json"
    if not os.path.exists(path):
        return set()
    with open(path, "r", encoding="utf-8") as f:
        return {item["id"] for item in json.load(f)}


async def _fetch_one(connector, label, query, start, end, seen_ids):
    """
    Runs one connector for one query, drops anything already seen (either
    from disk or from another connector/query earlier in this same run).
    Never raises — a single failed source/query shouldn't kill the batch.
    """
    try:
        articles = await connector.fetch_articles(query, start, end)
    except NewsAPIAuthError as e:
        print(f"  {label} skipped: {e}")
        return []
    except Exception as e:
        print(f"  {label} FAILED for '{query}': {e}")
        return []

    new = [a for a in articles if a.id not in seen_ids]
    for a in new:
        seen_ids.add(a.id)
    print(f"  {label} · '{query}': {len(articles)} fetched, {len(new)} new after dedup")
    return new


async def fetch_historical(queries: list[str], lookback_days: int) -> list:
    """
    Runs GDELT + NewsAPI concurrently across all configured queries.
    Per-source responses are cached in Redis (cache/api_cache.py) inside
    each connector, so re-running the same query/date-range within the
    cache TTL doesn't re-hit either API.
    """
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=lookback_days)
    seen_ids = _load_existing_ids()

    gdelt = GDELTConnector()
    newsapi = NewsAPIConnector()  # skipped per-query if NEWS_API_KEY isn't set

    tasks = []
    for q in queries:
        tasks.append(_fetch_one(gdelt, "GDELT", q, start, end, seen_ids))
        tasks.append(_fetch_one(newsapi, "NewsAPI", q, start, end, seen_ids))

    results = await asyncio.gather(*tasks)
    await gdelt.aclose()
    await newsapi.aclose()

    all_new = [a for batch in results for a in batch]

    # Per-run raw dump for audit/history — data/raw/ is gitignored, same as
    # data/raw_news.json, so this is local-only, not committed.
    os.makedirs(RAW_DIR, exist_ok=True)
    stamp = end.strftime("%Y%m%dT%H%M%SZ")
    dump_path = os.path.join(RAW_DIR, f"historical_{stamp}.json")
    with open(dump_path, "w", encoding="utf-8") as f:
        json.dump(
            [a.model_dump(mode="json") for a in all_new],
            f, indent=2, ensure_ascii=False, default=str,
        )
    print(f"  Wrote {len(all_new)} deduplicated articles to {dump_path}")

    return all_new


async def main():
    print("\n── STEP 1: Fetching RSS news ──")
    rss_articles = fetch_news()
    save_news(rss_articles)

    print("\n── STEP 2: Fetching historical news (GDELT + NewsAPI) ──")
    queries = [
        q.strip() for q in os.getenv("INGEST_QUERIES", ",".join(DEFAULT_QUERIES)).split(",")
        if q.strip()
    ]
    lookback_days = int(os.getenv("INGEST_LOOKBACK_DAYS", 2))
    historical_articles = await fetch_historical(queries, lookback_days)

    # Reuses the existing save_news()/raw_news.json shape via to_legacy_dict(),
    # so preprocessing + embeddings below run completely unchanged.
    save_news([a.to_legacy_dict() for a in historical_articles])

    print("\n── STEP 3: Preprocessing ──")
    process_news()

    print("\n── STEP 4: Building vector DB ──")
    store_embeddings()

    print("\n✅ Pipeline complete. Ready for queries.")


if __name__ == "__main__":
    asyncio.run(main())