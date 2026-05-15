from ingestion.news_fetcher import fetch_news, save_news
from preprocessing.preprocess import process_news, extract_entities
from embeddings.embed_store import store_embeddings
from retrieval.retrieve import search
from models.sentiment import get_sentiment
from models.outcome import predict_outcome
from models.llm_explainer import generate_llm_explanation

# ============================================
# STEP 1: UPDATE NEWS DATABASE
# ============================================

print("\n🚀 FETCHING LATEST NEWS")

news = fetch_news()
save_news(news)

print("\n🚀 PROCESSING NEWS")
process_news()

print("\n🚀 GENERATING EMBEDDINGS")
# run only ONCE per update cycle
news = fetch_news()
save_news(news)

process_news()
store_embeddings()

print("\n✅ NEWS DATABASE UPDATED")

# ============================================
# STEP 2: USER QUERY SYSTEM
# ============================================

print("\n===== NEWS ANALYSIS SYSTEM =====")

while True:

    query = input("\n🔍 Enter news topic/query: ")

    if query.lower() == "exit":
        break

    # -----------------------------------
    # RETRIEVE NEWS
    # -----------------------------------

    results = search(query, top_k=1)

    if not results["documents"][0]:
        print("No relevant news found.")
        continue

    news_text = results["documents"][0][0]
    metadata = results["metadatas"][0][0]

    # -----------------------------------
    # AI ANALYSIS
    # -----------------------------------

    sentiment = get_sentiment(news_text)

    entities = extract_entities(news_text)

    impact = predict_outcome(news_text)

    explanation = generate_llm_explanation(
        news_text,
        sentiment,
        impact,
        entities
    )

    # -----------------------------------
    # OUTPUT
    # -----------------------------------

    print("\n==============================")
    print("📰 NEWS:")
    print(news_text)

    print("\n🔍 Sentiment:", sentiment)

    print("\n🏷 Entities:")
    print(entities)

    print("\n📊 Impact:", impact)

    print("\n🧠 Explanation:")
    print(explanation)

    print("\n🌐 Source:", metadata["source"])