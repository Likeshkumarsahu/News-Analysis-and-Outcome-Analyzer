from ingestion.news_fetcher import fetch_news, save_news
from preprocessing.preprocess import process_news
from embeddings.embed_store import store_embeddings

print("\n── STEP 1: Fetching news ──")
news = fetch_news()
save_news(news)

print("\n── STEP 2: Preprocessing ──")
process_news()

print("\n── STEP 3: Building vector DB ──")
store_embeddings()

print("\n✅ Pipeline complete. Ready for queries.")