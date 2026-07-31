import os
import time
import requests
import ollama

OLLAMA_HOST  = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = "llama3.2:3b"

# Free Groq models (as of writing — verify at console.groq.com)
GROQ_FREE_MODELS = [
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
    "gemma2-9b-it",
    "mixtral-8x7b-32768",
]


def check_ollama_connected() -> dict:
    """
    Check if Ollama is running and reachable, and the required model is pulled.
    Returns: {"connected": bool, "model_available": bool, "message": str}
    """
    try:
        resp = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=3)
        if resp.status_code != 200:
            return {"connected": False, "model_available": False,
                    "message": f"Ollama responded with status {resp.status_code}"}

        models = [m["name"] for m in resp.json().get("models", [])]
        has_model = any(OLLAMA_MODEL in m for m in models)

        if not has_model:
            return {"connected": True, "model_available": False,
                    "message": f"Ollama is running but '{OLLAMA_MODEL}' is not pulled. "
                               f"Run: ollama pull {OLLAMA_MODEL}"}

        return {"connected": True, "model_available": True, "message": "OK"}

    except requests.exceptions.RequestException as e:
        return {"connected": False, "model_available": False,
                "message": f"Cannot reach Ollama at {OLLAMA_HOST}: {e}"}


def _build_prompt(query, retrieved_articles, sentiment, outcome) -> str:
    context_parts = []
    for i, art in enumerate(retrieved_articles[:3], 1):
        context_parts.append(
            f"Article {i} [{art.get('source', 'Unknown')}]:\n"
            f"Title: {art.get('title', '')}\n"
            f"Summary: {art.get('text', '')[:250]}"
        )
    context = "\n\n".join(context_parts)

    return f"""You are a news analyst. Answer the query using the articles below.

Query: {query}

News Context:
{context}

Sentiment: {sentiment['label']} (confidence: {sentiment['confidence']})
Impact: {outcome['impact']} (confidence: {outcome['confidence']})
Signals: {', '.join(outcome['matched']) if outcome['matched'] else 'none'}

Give a concise answer in under 150 words:
1. Answer the query directly
2. Why sentiment is {sentiment['label']}
3. Why impact is {outcome['impact']}
4. 2 likely outcomes

Response:"""


def _explain_local(prompt: str) -> str:
    """Run explanation via local Ollama."""
    status = check_ollama_connected()
    if not status["connected"] or not status["model_available"]:
        return f"LLM explanation unavailable: {status['message']}"

    client = ollama.Client(host=OLLAMA_HOST)
    try:
        response = client.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"num_predict": 250, "num_ctx": 768, "temperature": 0.3},
        )
        return response["message"]["content"].strip()
    except Exception as e:
        return f"LLM explanation unavailable: {e}"


def _explain_groq(prompt: str, groq_model: str, groq_api_key: str) -> str:
    """Run explanation via Groq cloud API."""
    if not groq_api_key:
        return "LLM explanation unavailable: Groq API key is required."
    if groq_model not in GROQ_FREE_MODELS:
        return f"LLM explanation unavailable: '{groq_model}' is not a supported free Groq model."

    try:
        from groq import Groq
        client = Groq(api_key=groq_api_key)
        response = client.chat.completions.create(
            model=groq_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"LLM explanation unavailable (Groq): {e}"


def explain(
    query: str,
    retrieved_articles: list,
    sentiment: dict,
    outcome: dict,
    provider: str = "local",
    groq_model: str = None,
    groq_api_key: str = None,
) -> str:
    """
    Generate explanation using either local Ollama or Groq cloud.

    Args:
        provider: "local" or "groq"
        groq_model: required if provider="groq" — must be in GROQ_FREE_MODELS
        groq_api_key: required if provider="groq" — user's own Groq API key
    """
    prompt = _build_prompt(query, retrieved_articles, sentiment, outcome)

    if provider == "groq":
        return _explain_groq(prompt, groq_model, groq_api_key)

    # default: local
    return _explain_local(prompt)