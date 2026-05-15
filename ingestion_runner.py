from ingestion.news_fetcher import fetch_news, save_news
from preprocessing.preprocess import process_news
from embeddings.embed_store import store_embeddings

print("\n🚀 FETCHING NEWS")
news = fetch_news()
save_news(news)

print("\n🚀 PROCESSING")
process_news()

print("\n🚀 BUILDING VDB")
store_embeddings()

print("\n✅ READY FOR DEMO")