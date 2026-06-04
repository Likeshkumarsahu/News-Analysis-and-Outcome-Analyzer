import feedparser
import hashlib
import json
import os
from datetime import datetime

# ── RSS feed sources ──────────────────────────────────────────────────────────
RSS_FEEDS = {
    "BBC":         "http://feeds.bbci.co.uk/news/rss.xml",
    "Economic Times": "https://economictimes.indiatimes.com/rssfeedsdefault.cms",
    "Al Jazeera":  "https://www.aljazeera.com/xml/rss/all.xml",
    "The Hindu":   "https://www.thehindu.com/news/feeder/default.rss",
    "NDTV":        "https://feeds.feedburner.com/ndtvnews-top-stories",
    "Financial Express": "https://syndication.financialexpress.com/rss/latest-news.xml",
    "Mint": "https://www.livemint.com/rss/homepage"
}

RAW_PATH = "data/raw_news.json"
os.makedirs("data", exist_ok=True)


def _make_id(title: str, link: str) -> str:
    """Stable unique ID based on title + URL — used for deduplication."""
    return hashlib.md5(f"{title}{link}".encode()).hexdigest()


def _load_existing_ids() -> set:
    """Load IDs already saved so we never store duplicates."""
    if not os.path.exists(RAW_PATH):
        return set()
    with open(RAW_PATH, "r", encoding="utf-8") as f:
        existing = json.load(f)
    return {item["id"] for item in existing}


def fetch_news() -> list[dict]:
    """
    Fetch articles from all RSS feeds.
    Returns only NEW articles (not already in raw_news.json).
    """
    existing_ids = _load_existing_ids()
    new_articles = []

    for source, url in RSS_FEEDS.items():
        print(f"  Fetching: {source} ...", end=" ")
        try:
            feed = feedparser.parse(url)
            count = 0
            for entry in feed.entries:
                title   = entry.get("title", "").strip()
                link    = entry.get("link", "").strip()
                summary = entry.get("summary", "").strip()

                if not title or not link:
                    continue

                article_id = _make_id(title, link)
                if article_id in existing_ids:
                    continue  # skip duplicate

                published = entry.get("published", "")
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    try:
                        published = datetime(*entry.published_parsed[:6]).isoformat()
                    except Exception:
                        pass

                new_articles.append({
                    "id":        article_id,
                    "source":    source,
                    "title":     title,
                    "summary":   summary,
                    "link":      link,
                    "published": published,
                    "fetched_at": datetime.now().isoformat(),
                })
                existing_ids.add(article_id)
                count += 1

            print(f"{count} new articles")

        except Exception as e:
            print(f"FAILED — {e}")

    return new_articles


def save_news(articles: list[dict]) -> None:
    """
    Append new articles to raw_news.json.
    Never overwrites — always appends, so old articles are preserved.
    """
    if not articles:
        print("  No new articles to save.")
        return

    existing = []
    if os.path.exists(RAW_PATH):
        with open(RAW_PATH, "r", encoding="utf-8") as f:
            existing = json.load(f)

    combined = existing + articles

    with open(RAW_PATH, "w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)

    print(f"  Saved {len(articles)} new articles. Total in DB: {len(combined)}")


def load_news() -> list[dict]:
    """Load all saved articles from raw_news.json."""
    if not os.path.exists(RAW_PATH):
        print("  raw_news.json not found. Run fetch_news() first.")
        return []
    with open(RAW_PATH, "r", encoding="utf-8") as f:
        return json.load(f)