import json
import re
import os
import spacy

RAW_PATH      = "data/raw_news.json"
PROCESSED_PATH = "data/processed_news.json"

# Load SpaCy model once at module level (not inside the function)
print("  Loading SpaCy model...")
nlp = spacy.load("en_core_web_sm")


def _clean_text(text: str) -> str:
    """
    Remove HTML tags, extra whitespace, special chars.
    Keep sentence structure intact for embeddings.
    """
    text = re.sub(r"<[^>]+>", " ", text)          # strip HTML
    text = re.sub(r"http\S+|www\S+", " ", text)    # strip URLs
    text = re.sub(r"[^\w\s.,!?'-]", " ", text)     # strip junk chars
    text = re.sub(r"\s+", " ", text).strip()        # collapse whitespace
    return text


def _extract_entities(text: str) -> dict:
    """
    Run SpaCy NER. Returns dict of entity types → list of values.
    e.g. {"ORG": ["Google", "WHO"], "GPE": ["India"], "PERSON": ["Modi"]}
    """
    doc = nlp(text[:1000])  # cap at 1000 chars — enough for news summary
    entities = {}
    for ent in doc.ents:
        label = ent.label_
        value = ent.text.strip()
        if label not in entities:
            entities[label] = []
        if value not in entities[label]:
            entities[label].append(value)
    return entities


def _build_full_text(article: dict) -> str:
    """
    Combine title + summary into a single string for embedding.
    Title gets repeated to give it more weight.
    """
    title   = article.get("title", "")
    summary = article.get("summary", "")
    return f"{title}. {title}. {summary}".strip()


def process_news() -> list[dict]:
    """
    Load raw_news.json, clean + extract entities, save to processed_news.json.
    Only processes articles not already in processed_news.json (incremental).
    """
    # Load raw
    if not os.path.exists(RAW_PATH):
        print("  raw_news.json not found. Run fetch_news() first.")
        return []

    with open(RAW_PATH, "r", encoding="utf-8") as f:
        raw_articles = json.load(f)

    # Load already-processed IDs to skip
    existing_processed = []
    existing_ids = set()
    if os.path.exists(PROCESSED_PATH):
        with open(PROCESSED_PATH, "r", encoding="utf-8") as f:
            existing_processed = json.load(f)
        existing_ids = {a["id"] for a in existing_processed}

    new_processed = []
    skipped = 0

    for article in raw_articles:
        article_id = article.get("id")

        if article_id in existing_ids:
            skipped += 1
            continue

        title   = _clean_text(article.get("title", ""))
        summary = _clean_text(article.get("summary", ""))

        if not title:
            continue  # skip empty articles

        full_text = _build_full_text({"title": title, "summary": summary})
        entities  = _extract_entities(full_text)

        new_processed.append({
            "id":         article_id,
            "source":     article.get("source", ""),
            "title":      title,
            "summary":    summary,
            "full_text":  full_text,
            "entities":   entities,
            "link":       article.get("link", ""),
            "published":  article.get("published", ""),
            "fetched_at": article.get("fetched_at", ""),
        })

    # Append and save
    combined = existing_processed + new_processed
    os.makedirs("data", exist_ok=True)
    with open(PROCESSED_PATH, "w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)

    print(f"  Processed {len(new_processed)} new articles. "
          f"Skipped {skipped} already done. "
          f"Total: {len(combined)}")

    return new_processed


def load_processed() -> list[dict]:
    """Load all processed articles."""
    if not os.path.exists(PROCESSED_PATH):
        print("  processed_news.json not found. Run process_news() first.")
        return []
    with open(PROCESSED_PATH, "r", encoding="utf-8") as f:
        return json.load(f)