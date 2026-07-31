import os
import json
import chromadb
from sentence_transformers import SentenceTransformer
from preprocessing.preprocess import load_processed

os.environ["TRANSFORMERS_OFFLINE"] = "0"
os.environ["HF_DATASETS_OFFLINE"] = "0"

# ── Config ────────────────────────────────────────────────────────────────────
CHROMA_PATH = "storage/chroma"
COLLECTION  = "news"
BATCH_SIZE  = 32          # safe for CPU RAM — old code used 64, can OOM
MODEL_NAME  = "BAAI/bge-small-en-v1.5"

os.makedirs(CHROMA_PATH, exist_ok=True)

# Load model once at module level
print("  Loading embedding model...")
_model = SentenceTransformer(MODEL_NAME)

# ChromaDB persistent client
_client     = chromadb.PersistentClient(path=CHROMA_PATH)
_collection = _client.get_or_create_collection(
    name=COLLECTION,
    metadata={"hnsw:space": "cosine"},   # cosine similarity — better for text
)


def _already_stored_ids() -> set:
    """Return all IDs already in ChromaDB to skip re-embedding."""
    result = _collection.get(include=[])   # only fetch IDs, no vectors
    return set(result["ids"])


def store_embeddings() -> None:
    """
    Load processed_news.json, embed full_text, store in ChromaDB.
    Incremental — only embeds articles not already in the DB.
    Batched — won't OOM on CPU.
    """
    articles = load_processed()
    if not articles:
        print("  No processed articles found.")
        return

    existing_ids = _already_stored_ids()
    print(f"  ChromaDB already has {len(existing_ids)} chunks.")

    # Filter to only new articles
    new_articles = [a for a in articles if a["id"] not in existing_ids]
    if not new_articles:
        print("  Nothing new to embed. ChromaDB is up to date.")
        return

    print(f"  Embedding {len(new_articles)} new articles in batches of {BATCH_SIZE}...")

    total_stored = 0

    for i in range(0, len(new_articles), BATCH_SIZE):
        batch = new_articles[i : i + BATCH_SIZE]

        ids       = [a["id"]        for a in batch]
        texts     = [a["full_text"] for a in batch]
        metadatas = [
            {
                "source":    a.get("source", ""),
                "title":     a.get("title", "")[:200],   # ChromaDB metadata limit
                "link":      a.get("link", "")[:500],
                "published": a.get("published", ""),
                "entities":  json.dumps(a.get("entities", {})),  # store as JSON string
            }
            for a in batch
        ]

        embeddings = _model.encode(
            texts,
            show_progress_bar=False,
            batch_size=BATCH_SIZE,
        ).tolist()

        _collection.add(
            ids=ids,
            documents=texts,
            metadatas=metadatas,
            embeddings=embeddings,
        )

        total_stored += len(batch)
        print(f"  Stored batch {i // BATCH_SIZE + 1} | {total_stored}/{len(new_articles)}")

    print(f"  Done. Total chunks in ChromaDB: {_collection.count()}")


def get_collection():
    """Return the ChromaDB collection — used by retrieval module."""
    return _collection


def get_model():
    """Return the embedding model — used by retrieval module."""
    return _model