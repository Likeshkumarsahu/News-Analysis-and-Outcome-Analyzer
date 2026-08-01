import os
import time
import litellm
from litellm import completion

litellm.drop_params = True  # ignore unsupported kwargs per-provider silently

# ── Cost per 1K tokens (approx, input+output blended) — used for tracking only ──
COST_PER_1K = {
    "claude-3-5-sonnet-20241022": 0.006,
    "gpt-4o":                      0.005,
    "gpt-4o-mini":                 0.0003,
    "gemini/gemini-1.5-flash":     0.0002,
    "groq/llama-3.3-70b-versatile":0.0,     # free tier
    "ollama/llama3.2:3b":          0.0,     # local, free
}

# ── Fallback order: cloud premium → cloud free → local ──
FALLBACK_CHAIN = [
    {"model": "claude-3-5-sonnet-20241022", "key_env": "ANTHROPIC_API_KEY"},
    {"model": "gpt-4o-mini",                "key_env": "OPENAI_API_KEY"},
    {"model": "gemini/gemini-1.5-flash",    "key_env": "GEMINI_API_KEY"},
    {"model": "groq/llama-3.3-70b-versatile","key_env": "GROQ_API_KEY"},
    {"model": "ollama/llama3.2:3b",         "key_env": None},  # always last resort
]

PROVIDER_DISPLAY = {
    "claude-3-5-sonnet-20241022":  "Anthropic Claude",
    "gpt-4o-mini":                 "OpenAI GPT-4o mini",
    "gemini/gemini-1.5-flash":     "Google Gemini",
    "groq/llama-3.3-70b-versatile":"Groq",
    "ollama/llama3.2:3b":          "Local (Ollama)",
}


def _usable_chain(user_provider: str, user_model: str, user_key: str) -> list:
    """
    Build the actual call chain for this request.
    If user explicitly picked a provider+key, try that first, then fall back
    through FALLBACK_CHAIN for resilience.
    """
    chain = []
    if user_provider == "local":
        chain.append({"model": "ollama/llama3.2:3b", "key_env": None, "api_key": None})
        return chain

    if user_provider and user_model and user_key:
        chain.append({"model": user_model, "key_env": None, "api_key": user_key})

    # Always append the standard fallback chain after the user's explicit choice
    for step in FALLBACK_CHAIN:
        api_key = os.getenv(step["key_env"]) if step["key_env"] else None
        if step["key_env"] and not api_key:
            continue  # skip providers with no key configured server-side
        chain.append({"model": step["model"], "key_env": step["key_env"], "api_key": api_key})

    return chain


def call_llm(prompt: str, user_provider: str = "local", user_model: str = None,
             user_key: str = None, max_tokens: int = 300) -> dict:
    """
    Try each provider in the fallback chain until one succeeds.

    Returns:
        {
            "text": str,
            "provider_used": str,
            "model_used": str,
            "cost_usd": float,
            "latency_ms": int,
            "fallback_hops": int,   # how many providers were tried before success
        }
    """
    chain = _usable_chain(user_provider, user_model, user_key)
    if not chain:
        return {"text": "No LLM provider available.", "provider_used": None,
                "model_used": None, "cost_usd": 0.0, "latency_ms": 0, "fallback_hops": 0}

    last_error = None
    for hop, step in enumerate(chain):
        model = step["model"]
        try:
            start = time.time()
            kwargs = {"model": model, "messages": [{"role": "user", "content": prompt}],
                      "max_tokens": max_tokens, "timeout": 60}
            if step.get("api_key"):
                kwargs["api_key"] = step["api_key"]
            if model.startswith("ollama/"):
                kwargs["api_base"] = os.getenv("OLLAMA_HOST", "http://localhost:11434")

            response = completion(**kwargs)
            latency = int((time.time() - start) * 1000)

            text = response.choices[0].message.content.strip()

            usage = getattr(response, "usage", None)
            total_tokens = (usage.total_tokens if usage else 0) or 0
            cost = COST_PER_1K.get(model, 0.0) * (total_tokens / 1000)

            return {
                "text": text,
                "provider_used": PROVIDER_DISPLAY.get(model, model),
                "model_used": model,
                "cost_usd": round(cost, 6),
                "latency_ms": latency,
                "fallback_hops": hop,
            }

        except Exception as e:
            last_error = e
            continue

    return {"text": f"All providers failed. Last error: {last_error}",
            "provider_used": None, "model_used": None, "cost_usd": 0.0,
            "latency_ms": 0, "fallback_hops": len(chain)}