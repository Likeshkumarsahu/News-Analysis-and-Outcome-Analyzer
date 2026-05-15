import json
import os
import chromadb
from sentence_transformers import SentenceTransformer

# ---------------- PATHS ----------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_PATH = os.path.join(BASE_DIR, "data", "processed", "processed_news.json")
CHROMA_PATH = os.path.join(BASE_DIR, "chroma")

# ---------------- MODEL ----------------
model = SentenceTransformer("all-MiniLM-L6-v2")

# ---------------- CHROMA (FIXED) ----------------
client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = client.get_or_create_collection(name="news")


# ---------------- DUPLICATE CHECK ----------------
def is_duplicate(text, existing_docs):
    text = text.strip().lower()

    for d in existing_docs:
        d = d.strip().lower()

        # stronger similarity check
        if text[:200] == d[:200]:
            return True

    return False


# ---------------- STORE EMBEDDINGS ----------------
def store_embeddings():

    if not os.path.exists(DATA_PATH):
        print("❌ No processed data found")
        return

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    existing = collection.get(include=["documents"])
    existing_docs = existing.get("documents", [])

    ids, docs, metas = [], [], []

    for i, article in enumerate(data):
        for j, chunk in enumerate(article["chunks"]):

            if is_duplicate(chunk, existing_docs):
                continue

            ids.append(f"{i}_{j}")
            docs.append(chunk)

            metas.append({
                "title": article["title"],
                "source": article["source"],
                "published": article["published"],
                "topic": article.get("topic", "general")
            })

    if not docs:
        print("⚠️ No new data to store")
        return

    embeddings = model.encode(docs).tolist()

    collection.add(
        ids=ids,
        documents=docs,
        metadatas=metas,
        embeddings=embeddings
    )

    print(f"✅ Stored {len(docs)} NEW chunks in Vector DB")