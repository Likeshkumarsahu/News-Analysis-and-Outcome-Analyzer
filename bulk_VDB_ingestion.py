import os
import feedparser
import chromadb

from sentence_transformers import SentenceTransformer

# ---------------- SETTINGS ----------------
TARGET_CHUNKS = 10000
BATCH_SIZE = 64

# ---------------- PATHS ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_PATH = os.path.join(BASE_DIR, "chroma")

# ---------------- MODEL ----------------
model = SentenceTransformer("all-MiniLM-L6-v2")

# ---------------- CHROMA ----------------
client = chromadb.PersistentClient(path=CHROMA_PATH)

collection = client.get_or_create_collection(
    name="news"
)

# ---------------- RSS SOURCES ----------------
RSS_FEEDS = {

    # BBC
    "BBC World": "http://feeds.bbci.co.uk/news/world/rss.xml",
    "BBC Politics": "http://feeds.bbci.co.uk/news/politics/rss.xml",
    "BBC Business": "http://feeds.bbci.co.uk/news/business/rss.xml",
    "BBC Tech": "http://feeds.bbci.co.uk/news/technology/rss.xml",

    # Reuters
    "Reuters World": "http://feeds.reuters.com/Reuters/worldNews",
    "Reuters Business": "http://feeds.reuters.com/reuters/businessNews",
    "Reuters Technology": "http://feeds.reuters.com/reuters/technologyNews",

    # CNN
    "CNN Top": "http://rss.cnn.com/rss/edition.rss",
    "CNN World": "http://rss.cnn.com/rss/edition_world.rss",
    "CNN Technology": "http://rss.cnn.com/rss/edition_technology.rss",

    # Guardian
    "Guardian World": "https://www.theguardian.com/world/rss",
    "Guardian Technology": "https://www.theguardian.com/uk/technology/rss",
    "Guardian Business": "https://www.theguardian.com/uk/business/rss",

    # Al Jazeera
    "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",

    # NYTimes
    "NYTimes World": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "NYTimes Technology": "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",

    # Fox
    "Fox News": "http://feeds.foxnews.com/foxnews/latest",

    # NPR
    "NPR": "https://feeds.npr.org/1001/rss.xml"
}

# ---------------- TOPIC DETECTOR ----------------
def get_topic(text):

    text = text.lower()

    if any(k in text for k in [
        "election", "government", "war",
        "president", "minister", "policy"
    ]):
        return "politics"

    if any(k in text for k in [
        "ai", "technology", "software",
        "google", "microsoft", "startup"
    ]):
        return "tech"

    if any(k in text for k in [
        "market", "economy", "finance",
        "inflation", "stock"
    ]):
        return "economy"

    if any(k in text for k in [
        "football", "cricket",
        "sports", "tournament"
    ]):
        return "sports"

    return "world"

# ---------------- CLEAN ----------------
def clean_text(text):

    if not text:
        return ""

    text = text.replace("\n", " ")
    text = text.replace("\r", " ")

    return text.strip()

# ---------------- CHUNK ----------------
def chunk_text(text, size=120):

    words = text.split()

    return [
        " ".join(words[i:i+size])
        for i in range(0, len(words), size)
    ]

# ---------------- DEDUP ----------------
def make_hash(text):

    return hash(
        text[:300].strip().lower()
    )

# ---------------- MAIN ----------------
def build_vdb():

    print("\n🚀 BUILDING CLEAN NEWS VECTOR DB\n")

    all_docs = []
    all_metas = []
    all_ids = []

    total_chunks = 0
    skipped_duplicates = 0

    # old data safe
    unique_id = collection.count()

    # existing docs for dedup
    existing = collection.get(include=["documents"])

    existing_docs = existing.get("documents", [])

    existing_hashes = set()

    for doc in existing_docs:
        existing_hashes.add(
            make_hash(doc)
        )

    print(f"🧠 Existing DB chunks: {len(existing_docs)}")

    for source, url in RSS_FEEDS.items():

        print(f"\n🌐 Fetching: {source}")

        try:

            feed = feedparser.parse(url)

            for article in feed.entries:

                title = clean_text(
                    article.get("title", "")
                )

                summary = clean_text(
                    article.get("summary", "")
                )

                if len(summary) < 80:
                    continue

                topic = get_topic(
                    title + " " + summary
                )

                content = f"{title}. {summary}"

                chunks = chunk_text(content)

                for chunk in chunks:

                    h = make_hash(chunk)

                    # ---------------- DEDUP ----------------
                    if h in existing_hashes:
                        skipped_duplicates += 1
                        continue

                    existing_hashes.add(h)

                    all_docs.append(chunk)

                    all_metas.append({
                        "source": source,
                        "title": title,
                        "topic": topic,
                        "published": article.get(
                            "published",
                            ""
                        )
                    })

                    all_ids.append(
                        f"news_{unique_id}"
                    )

                    unique_id += 1
                    total_chunks += 1

                    # ---------------- BATCH INSERT ----------------
                    if len(all_docs) >= BATCH_SIZE:

                        embeddings = model.encode(
                            all_docs,
                            show_progress_bar=False
                        ).tolist()

                        collection.add(
                            ids=all_ids,
                            documents=all_docs,
                            metadatas=all_metas,
                            embeddings=embeddings
                        )

                        print(
                            f"📦 Stored batch | Total NEW chunks: {total_chunks}"
                        )

                        all_docs = []
                        all_metas = []
                        all_ids = []

                    # ---------------- LIMIT ----------------
                    if total_chunks >= TARGET_CHUNKS:
                        break

                if total_chunks >= TARGET_CHUNKS:
                    break

            if total_chunks >= TARGET_CHUNKS:
                break

        except Exception as e:

            print(f"❌ ERROR: {e}")

    # ---------------- FINAL INSERT ----------------
    if all_docs:

        embeddings = model.encode(
            all_docs,
            show_progress_bar=False
        ).tolist()

        collection.add(
            ids=all_ids,
            documents=all_docs,
            metadatas=all_metas,
            embeddings=embeddings
        )

    # ---------------- FINAL STATS ----------------
    final_count = collection.count()

    print("\n==============================")
    print(f"✅ NEW chunks added: {total_chunks}")
    print(f"⏭️ Duplicates skipped: {skipped_duplicates}")
    print(f"🧠 TOTAL DB CHUNKS: {final_count}")
    print("==============================")

# ---------------- RUN ----------------
if __name__ == "__main__":
    build_vdb()