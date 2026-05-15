import os
import json
import random
import chromadb
import traceback

from sentence_transformers import SentenceTransformer

# =====================================================
# PATHS
# =====================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_FOLDER = os.path.join(
    BASE_DIR,
    "data",
    "bulkNews"
)

CHROMA_PATH = os.path.join(
    BASE_DIR,
    "chroma"
)

# =====================================================
# SETTINGS
# =====================================================

CHUNK_SIZE = 120
BATCH_SIZE = 64

# 🔥 LIMIT PER FILE
MAX_ARTICLES_PER_FILE = 5000

# =====================================================
# MODEL
# =====================================================

print("\n🧠 Loading embedding model...\n")

model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)

# =====================================================
# CHROMADB
# =====================================================

client = chromadb.PersistentClient(
    path=CHROMA_PATH
)

collection = client.get_or_create_collection(
    name="news"
)

# =====================================================
# CLEAN TEXT
# =====================================================

def clean_text(text):

    if text is None:
        return ""

    text = str(text)

    text = text.replace("\n", " ")
    text = text.replace("\r", " ")
    text = text.replace("\t", " ")

    text = " ".join(text.split())

    return text.strip()

# =====================================================
# ENGLISH DETECTOR
# =====================================================

def looks_english(text):

    if not text:
        return False

    text = text.lower()

    english_words = [
        "the", "and", "is", "are",
        "was", "were", "government",
        "market", "technology",
        "president", "news",
        "people", "world",
        "business", "sports",
        "minister", "economy",
        "international", "company"
    ]

    score = 0

    for word in english_words:

        if word in text:
            score += 1

    # unicode filter
    ascii_ratio = sum(
        c.isascii() for c in text
    ) / max(len(text), 1)

    return score >= 2 and ascii_ratio > 0.85

# =====================================================
# CHUNKING
# =====================================================

def chunk_text(text, size=CHUNK_SIZE):

    words = text.split()

    if len(words) <= size:
        return [text]

    return [
        " ".join(words[i:i+size])
        for i in range(0, len(words), size)
    ]

# =====================================================
# HASH FOR DEDUP
# =====================================================

def make_hash(text):

    return hash(
        text[:500].lower().strip()
    )

# =====================================================
# QUALITY FILTER
# =====================================================

def is_quality_news(title, content):

    if not title or not content:
        return False

    score = 0

    if len(title) > 20:
        score += 1

    if len(content) > 250:
        score += 2

    if len(content.split()) > 40:
        score += 1

    bad_words = [
        "advertisement",
        "subscribe",
        "click here",
        "sponsored",
        "sign up",
        "cookies policy"
    ]

    combined = (
        title + " " + content
    ).lower()

    if any(
        word in combined
        for word in bad_words
    ):
        return False

    return score >= 3

# =====================================================
# TOPIC DETECTOR
# =====================================================

def get_topic(text):

    text = text.lower()

    if any(k in text for k in [
        "war",
        "election",
        "government",
        "policy",
        "minister",
        "president"
    ]):
        return "politics"

    if any(k in text for k in [
        "ai",
        "technology",
        "software",
        "google",
        "microsoft",
        "startup"
    ]):
        return "tech"

    if any(k in text for k in [
        "market",
        "economy",
        "finance",
        "stock",
        "inflation"
    ]):
        return "economy"

    if any(k in text for k in [
        "football",
        "sports",
        "cricket",
        "tournament",
        "match"
    ]):
        return "sports"

    return "world"

# =====================================================
# SAFE ARTICLE PARSER
# =====================================================

def extract_article(article):

    possible_title_fields = [
        "title",
        "headline",
        "news_title"
    ]

    possible_content_fields = [
        "content",
        "description",
        "summary",
        "text",
        "body"
    ]

    title = ""
    content = ""

    for field in possible_title_fields:

        if field in article:

            title = clean_text(
                article.get(field)
            )

            if title:
                break

    for field in possible_content_fields:

        if field in article:

            content = clean_text(
                article.get(field)
            )

            if content:
                break

    return title, content

# =====================================================
# MAIN INGESTION
# =====================================================

def ingest_bulk_news():

    print("\n🚀 STARTING MASS NEWS INGESTION\n")

    # =================================================
    # EXISTING DOCS
    # =================================================

    existing = collection.get(
        include=["documents"]
    )

    existing_docs = existing.get(
        "documents",
        []
    )

    existing_hashes = set()

    for doc in existing_docs:

        existing_hashes.add(
            make_hash(doc)
        )

    print(
        f"🧠 Existing DB chunks: {len(existing_docs)}"
    )

    # =================================================
    # STATS
    # =================================================

    stored_chunks = 0
    skipped_duplicates = 0
    skipped_non_english = 0
    skipped_low_quality = 0
    broken_articles = 0

    unique_id = collection.count()

    # =================================================
    # BATCHES
    # =================================================

    docs_batch = []
    metas_batch = []
    ids_batch = []

    # =================================================
    # LOOP FILES
    # =================================================

    files = os.listdir(DATA_FOLDER)

    json_files = [
        f for f in files
        if f.endswith(".json")
    ]

    print(
        f"\n📂 Found {len(json_files)} JSON files\n"
    )

    for file_name in json_files:

        file_path = os.path.join(
            DATA_FOLDER,
            file_name
        )

        print(f"\n📄 Processing: {file_name}")

        try:

            with open(
                file_path,
                "r",
                encoding="utf-8"
            ) as f:

                data = json.load(f)

        except Exception as e:

            print(f"❌ Failed reading {file_name}")
            print(e)

            continue

        # =================================================
        # HANDLE DIFFERENT JSON STRUCTURES
        # =================================================

        if isinstance(data, dict):

            if "results" in data:
                data = data["results"]

            elif "articles" in data:
                data = data["articles"]

            elif "data" in data:
                data = data["data"]

            else:
                data = [data]

        if not isinstance(data, list):

            print(
                f"⚠️ Invalid structure skipped: {file_name}"
            )

            continue

        total_articles = len(data)

        print(
            f"📰 Total articles: {total_articles}"
        )

        # =================================================
        # RANDOM LIMITER
        # =================================================

        if total_articles > MAX_ARTICLES_PER_FILE:

            data = random.sample(
                data,
                MAX_ARTICLES_PER_FILE
            )

            print(
                f"🎲 Randomly selected {MAX_ARTICLES_PER_FILE} articles"
            )

        # =================================================
        # LOOP ARTICLES
        # =================================================

        for article in data:

            try:

                if not isinstance(article, dict):
                    broken_articles += 1
                    continue

                title, content = extract_article(
                    article
                )

                # EMPTY CHECK
                if not title or not content:
                    broken_articles += 1
                    continue

                combined_text = (
                    title + " " + content
                )

                # ENGLISH FILTER
                if not looks_english(
                    combined_text
                ):

                    skipped_non_english += 1
                    continue

                # QUALITY FILTER
                if not is_quality_news(
                    title,
                    content
                ):

                    skipped_low_quality += 1
                    continue

                # TOPIC
                topic = get_topic(
                    combined_text
                )

                # CHUNKS
                chunks = chunk_text(
                    combined_text
                )

                # STORE CHUNKS
                for chunk in chunks:

                    h = make_hash(chunk)

                    # DEDUP
                    if h in existing_hashes:

                        skipped_duplicates += 1
                        continue

                    existing_hashes.add(h)

                    docs_batch.append(chunk)

                    metas_batch.append({

                        "title": title,

                        "source": clean_text(
                            article.get(
                                "source_name",
                                file_name
                            )
                        ),

                        "topic": topic,

                        "published": clean_text(
                            article.get(
                                "pubDate",
                                article.get(
                                    "published",
                                    ""
                                )
                            )
                        )

                    })

                    ids_batch.append(
                        f"news_{unique_id}"
                    )

                    unique_id += 1
                    stored_chunks += 1

                    # BATCH INSERT
                    if len(docs_batch) >= BATCH_SIZE:

                        embeddings = model.encode(
                            docs_batch,
                            show_progress_bar=False
                        ).tolist()

                        collection.add(
                            ids=ids_batch,
                            documents=docs_batch,
                            metadatas=metas_batch,
                            embeddings=embeddings
                        )

                        print(
                            f"📦 Stored chunks: {stored_chunks}"
                        )

                        docs_batch = []
                        metas_batch = []
                        ids_batch = []

            except Exception:

                broken_articles += 1

                traceback.print_exc()

                continue

    # =================================================
    # FINAL INSERT
    # =================================================

    if docs_batch:

        embeddings = model.encode(
            docs_batch,
            show_progress_bar=False
        ).tolist()

        collection.add(
            ids=ids_batch,
            documents=docs_batch,
            metadatas=metas_batch,
            embeddings=embeddings
        )

    # =================================================
    # FINAL STATS
    # =================================================

    print("\n==============================")
    print(f"✅ Stored chunks: {stored_chunks}")
    print(f"⏭️ Duplicates skipped: {skipped_duplicates}")
    print(f"🌍 Non-English skipped: {skipped_non_english}")
    print(f"🗑 Low-quality skipped: {skipped_low_quality}")
    print(f"⚠️ Broken articles skipped: {broken_articles}")
    print(f"🧠 TOTAL DB CHUNKS: {collection.count()}")
    print("==============================")

# =====================================================
# RUN
# =====================================================

if __name__ == "__main__":

    ingest_bulk_news()