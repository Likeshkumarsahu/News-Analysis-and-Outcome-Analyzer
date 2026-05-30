import ollama


def explain(
    query: str,
    retrieved_articles: list,
    sentiment: dict,
    outcome: dict,
) -> str:

    context_parts = []
    for i, art in enumerate(retrieved_articles[:3], 1):
        context_parts.append(
            f"Article {i} [{art.get('source', 'Unknown')}]:\n"
            f"Title: {art.get('title', '')}\n"
            f"Summary: {art.get('text', '')[:300]}"
        )
    context = "\n\n".join(context_parts)

    prompt = f"""You are a news analyst. Based on the articles below, answer the user's query clearly and concisely.

User Query: {query}

Retrieved News Context:
{context}

Analysis Results:
- Sentiment: {sentiment['label']} (confidence: {sentiment['confidence']})
- Impact Level: {outcome['impact']} (confidence: {outcome['confidence']})
- Impact signals: {', '.join(outcome['matched']) if outcome['matched'] else 'none'}

Instructions:
1. Directly answer the query using the news context.
2. Explain why the sentiment is {sentiment['label']}.
3. Explain why the impact is {outcome['impact']}.
4. Give 2-3 likely outcomes or consequences based on the news.
5. Keep the response under 200 words. Be factual, not speculative.

Response:"""

    try:
        # response = ollama.chat(
        #     model="mistral:latest",
        #     messages=[{"role": "user", "content": prompt}],
        #     options={"num_predict": 400},
        # )
        response = ollama.chat(
            model="mistral:latest",
            messages=[{"role": "user", "content": prompt}],
            options={
                "num_predict": 300,
                "num_ctx": 1024,    # ← reduce from default 4096 to 1024
                    },
        )
        return response["message"]["content"].strip()

    except Exception as e:
        return f"LLM explanation unavailable: {e}"