import feedparser
import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

RSS_FEEDS = {
    "BBC": "http://feeds.bbci.co.uk/news/rss.xml",
    "Reuters": "http://feeds.reuters.com/reuters/topNews"
}

# ---------------- TOPIC CLASSIFIER ----------------
def get_topic(text):
    text = text.lower()

    if any(k in text for k in ["war", "election", "government", "minister", "policy"]):
        return "politics"

    if any(k in text for k in ["ai", "tech", "software", "google", "apple", "startup"]):
        return "tech"

    if any(k in text for k in ["stock", "market", "economy", "inflation", "gdp", "finance"]):
        return "economy"

    if any(k in text for k in ["cricket", "football", "sports", "tournament"]):
        return "sports"

    return "world"


# ---------------- QUALITY FILTER ----------------
def is_quality(title, summary):
    text = (title + " " + summary).lower()

    if len(text) < 80:
        return False

    bad_words = ["advertisement", "sponsored", "click here", "subscribe"]
    if any(w in text for w in bad_words):
        return False

    return True


# ---------------- HOT SCORE ----------------
def hot_score(entry, source):
    score = 0

    if source == "Reuters":
        score += 2

    if "hour" in entry.get("published", "").lower():
        score += 2

    if len(entry.get("summary", "")) > 200:
        score += 1

    return score


# ---------------- FETCH ----------------
def fetch_news(limit_per_source=200):
    all_news = []

    for source, url in RSS_FEEDS.items():
        feed = feedparser.parse(url)

        for entry in feed.entries[:limit_per_source]:

            title = entry.get("title", "")
            summary = entry.get("summary", "")

            if not is_quality(title, summary):
                continue

            topic = get_topic(title + summary)

            all_news.append({
                "source": source,
                "title": title,
                "summary": summary,
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
                "topic": topic,
                "score": hot_score(entry, source)
            })

    # sort by hot score
    all_news.sort(key=lambda x: x["score"], reverse=True)

    return all_news[:50]


# ---------------- SAVE ----------------
def save_news(news):
    path = os.path.join(BASE_DIR, "data", "raw")
    os.makedirs(path, exist_ok=True)

    file_path = os.path.join(path, "news.json")

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(news, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(news)} quality news")