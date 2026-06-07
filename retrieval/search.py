import json
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder
from embeddings.embed_store import get_collection, get_model

# ── CrossEncoder for reranking ────────────────────────────────────────────────
# Lightweight model, runs on CPU fine
print("  Loading CrossEncoder reranker...")
_reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

# ── Cached corpus for BM25 ────────────────────────────────────────────────────
# Built once on first search call, reused after
_bm25        = None
_corpus_docs = []   # raw text of each chunk
_corpus_ids  = []   # corresponding IDs
_corpus_meta = []   # corresponding metadata


def _build_bm25_index():
    """
    Pull all documents from ChromaDB and build a BM25 index.
    Called once lazily on first search.
    """
    global _bm25, _corpus_docs, _corpus_ids, _corpus_meta

    collection = get_collection()
    total      = collection.count()

    if total == 0:
        print("  ChromaDB is empty. Run store_embeddings() first.")
        return

    print(f"  Building BM25 index over {total} chunks...")

    result = collection.get(
        include=["documents", "metadatas"],
        limit=total,
    )

    _corpus_docs = result["documents"]
    _corpus_ids  = result["ids"]
    _corpus_meta = result["metadatas"]

    # Tokenize: simple whitespace split — good enough for BM25
    tokenized = [doc.lower().split() for doc in _corpus_docs]
    _bm25 = BM25Okapi(tokenized)
    print(f"  BM25 index ready: {len(_corpus_docs)} chunks.")


def search(query: str, top_k: int = 5) -> list[dict]:
    """
    Hybrid search: BM25 + semantic → merged → CrossEncoder rerank.

    Steps:
      1. BM25 keyword search  → top 20 candidates
      2. Semantic vector search → top 20 candidates
      3. Merge, deduplicate
      4. CrossEncoder rerank  → return top_k

    Args:
        query:  user query string
        top_k:  how many results to return (default 5)

    Returns:
        list of dicts with keys: id, text, source, title, link,
                                 published, entities, score
    """
    global _bm25

    # Lazy build BM25 index
    if _bm25 is None:
        _build_bm25_index()

    if not _corpus_docs:
        return []

    CANDIDATE_POOL = 20   # how many each method fetches before merging

    # ── Step 1: BM25 keyword search ───────────────────────────────────────────
    tokenized_query = query.lower().split()
    bm25_scores     = _bm25.get_scores(tokenized_query)

    # Get top CANDIDATE_POOL indices by BM25 score
    bm25_top_idx = sorted(
        range(len(bm25_scores)),
        key=lambda i: bm25_scores[i],
        reverse=True
    )[:CANDIDATE_POOL]

    bm25_candidates = {
        _corpus_ids[i]: {
            "id":       _corpus_ids[i],
            "text":     _corpus_docs[i],
            "metadata": _corpus_meta[i],
            "bm25":     bm25_scores[i],
        }
        for i in bm25_top_idx
    }

    # ── Step 2: Semantic vector search ───────────────────────────────────────
    model      = get_model()
    collection = get_collection()

    query_embedding = model.encode(query).tolist()
    sem_results     = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(CANDIDATE_POOL, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    sem_candidates = {}
    for idx, doc_id in enumerate(sem_results["ids"][0]):
        sem_candidates[doc_id] = {
            "id":       doc_id,
            "text":     sem_results["documents"][0][idx],
            "metadata": sem_results["metadatas"][0][idx],
            "semantic": 1 - sem_results["distances"][0][idx],  # cosine sim
        }

    # ── Step 3: Merge + deduplicate ───────────────────────────────────────────
    all_ids    = set(bm25_candidates.keys()) | set(sem_candidates.keys())
    candidates = []

    for doc_id in all_ids:
        b = bm25_candidates.get(doc_id, {})
        s = sem_candidates.get(doc_id, {})

        # Use whichever source has the data
        text     = b.get("text")     or s.get("text", "")
        metadata = b.get("metadata") or s.get("metadata", {})

        candidates.append({
            "id":       doc_id,
            "text":     text,
            "metadata": metadata,
            "bm25":     b.get("bm25", 0.0),
            "semantic": s.get("semantic", 0.0),
        })

    # ── Step 4: CrossEncoder rerank ───────────────────────────────────────────
    pairs  = [(query, c["text"]) for c in candidates]
    scores = _reranker.predict(pairs)

    for i, candidate in enumerate(candidates):
        candidate["score"] = float(scores[i])

    # Sort by CrossEncoder score descending
    candidates.sort(key=lambda x: x["score"], reverse=True)

    # ── Format output ─────────────────────────────────────────────────────────
    results = []
    for c in candidates[:top_k]:
        meta     = c["metadata"]
        entities = {}
        try:
            entities = json.loads(meta.get("entities", "{}"))
        except Exception:
            pass

        results.append({
            "id":        c["id"],
            "text":      c["text"],
            "source":    meta.get("source", ""),
            "title":     meta.get("title", ""),
            "link":      meta.get("link", ""),
            "published": meta.get("published", ""),
            "entities":  entities,
            "score":     round(float(c["score"]), 3),
        })

    return results
