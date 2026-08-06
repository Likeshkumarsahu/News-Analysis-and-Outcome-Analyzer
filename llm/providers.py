import os
import time
import litellm
from litellm import completion

litellm.drop_params = True  # ignore unsupported kwargs per-provider silently

# ── Cost per 1K tokens (approx, input+output blended) — used for tracking only ──
# NOTE: these model IDs were last verified August 2026. Providers update their
# lineups often — recheck against each provider's docs if calls start failing
# with "model not found".
COST_PER_1K = {
    "claude-sonnet-5":              0.006,
    "claude-opus-4-8":              0.02,
    "claude-haiku-4-5-20251001":    0.001,
    "gpt-5.6-sol":                  0.030,
    "gpt-5.6-terra":                0.012,
    "gpt-5.6-luna":                 0.0006,
    "gemini/gemini-3.6-flash":      0.0005,
    "gemini/gemini-3.1-flash-lite": 0.0002,
    "groq/llama-3.3-70b-versatile": 0.0,     # free tier
    "groq/llama-3.1-8b-instant":    0.0,     # free tier
    "groq/openai/gpt-oss-120b":     0.0,     # free tier
    "groq/openai/gpt-oss-20b":      0.0,     # free tier
    "groq/qwen/qwen3.6-27b":        0.0,     # free tier
    "ollama/llama3.2:3b":           0.0,     # local, free
}

# ── Fallback order: cloud premium → cloud free → local ──
FALLBACK_CHAIN = [
    {"model": "claude-sonnet-5",              "key_env": "ANTHROPIC_API_KEY"},
    {"model": "gpt-5.6-terra",                "key_env": "OPENAI_API_KEY"},
    {"model": "gemini/gemini-3.6-flash",      "key_env": "GEMINI_API_KEY"},
    {"model": "groq/llama-3.3-70b-versatile", "key_env": "GROQ_API_KEY"},
    {"model": "ollama/llama3.2:3b",           "key_env": None},  # always last resort
]

PROVIDER_DISPLAY = {
    "claude-sonnet-5":               "Anthropic Claude",
    "claude-opus-4-8":               "Anthropic Claude",
    "claude-haiku-4-5-20251001":     "Anthropic Claude",
    "gpt-5.6-sol":                   "OpenAI GPT",
    "gpt-5.6-terra":                 "OpenAI GPT",
    "gpt-5.6-luna":                  "OpenAI GPT",
    "gemini/gemini-3.6-flash":       "Google Gemini",
    "gemini/gemini-3.1-flash-lite":  "Google Gemini",
    "groq/llama-3.3-70b-versatile":  "Groq",
    "groq/llama-3.1-8b-instant":     "Groq",
    "groq/openai/gpt-oss-120b":      "Groq",
    "groq/openai/gpt-oss-20b":       "Groq",
    "groq/qwen/qwen3.6-27b":         "Groq",
    "ollama/llama3.2:3b":            "Local (Ollama)",
}

# ── Selectable models per provider, for the frontend's provider dropdown ────
# `needs_key` tells the frontend whether to show an API-key input.
PROVIDER_MODELS = {
    "local": {
        "label": "Local (Ollama)",
        "needs_key": False,
        "models": ["ollama/llama3.2:3b"],
    },
    "groq": {
        "label": "Groq (Cloud, free tier)",
        "needs_key": True,
        "key_help": "Free key at console.groq.com",
        "models": [
            "groq/llama-3.1-8b-instant",
            "groq/llama-3.3-70b-versatile",
            "groq/openai/gpt-oss-120b",
            "groq/openai/gpt-oss-20b",
            "groq/qwen/qwen3.6-27b",
        ],
    },
    "anthropic": {
        "label": "Anthropic Claude",
        "needs_key": True,
        "key_help": "Key at console.anthropic.com",
        "models": [
            "claude-haiku-4-5-20251001",
            "claude-sonnet-5",
            "claude-opus-4-8",
        ],
    },
    "openai": {
        "label": "OpenAI GPT",
        "needs_key": True,
        "key_help": "Key at platform.openai.com",
        "models": [
            "gpt-5.6-luna",
            "gpt-5.6-terra",
            "gpt-5.6-sol",
        ],
    },
    "gemini": {
        "label": "Google Gemini",
        "needs_key": True,
        "key_help": "Free key at aistudio.google.com",
        "models": [
            "gemini/gemini-3.1-flash-lite",
            "gemini/gemini-3.6-flash",
        ],
    },
}


def _build_model(provider: str, model: str, api_key: str = None):
    """
    Returns a LangChain chat-model instance for the given provider/model.

    This is used by agents/news_crew.py's langgraph `create_react_agent()`
    calls (the "CrewAI Deep Analysis" multi-agent pipeline) — it needs an
    actual LangChain BaseChatModel object, not the litellm string-based
    call used by call_llm() below (which powers the single-shot
    /api/analyze explanation instead). Keep both — they serve different
    call paths and aren't interchangeable.

    `provider`/`model` now come from whatever the user picked in the
    website's provider selector (see agents/news_crew.py's run_news_crew),
    falling back to the CREW_PROVIDER / CREW_MODEL env vars only when the
    caller doesn't supply one (e.g. Local/Ollama, which needs no key).
    `api_key`, likewise, prefers the user-supplied key and falls back to
    the matching server-side env var.

    Model IDs here should be the provider's *native* format, not litellm's
    "provider/model" prefix style used in PROVIDER_MODELS above — since the
    frontend's model list DOES use that litellm-prefixed style (it's shared
    with call_llm), we defensively strip a stray "groq/" or "gemini/"
    prefix so a model picked in the UI still resolves correctly here.
    """
    provider = (provider or "local").lower()
    if model:
        for prefix in ("groq/", "gemini/"):
            if model.startswith(prefix):
                model = model[len(prefix):]

    if provider == "local":
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=model or "llama3.2:3b",
            base_url=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            temperature=0.3,
        )

    if provider == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(
            model=model or "llama-3.3-70b-versatile",
            api_key=api_key or os.getenv("GROQ_API_KEY"),
            temperature=0.3,
        )

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=model or "claude-sonnet-5",
            api_key=api_key or os.getenv("ANTHROPIC_API_KEY"),
            temperature=0.3,
        )

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model or "gpt-5.6-terra",
            api_key=api_key or os.getenv("OPENAI_API_KEY"),
            temperature=0.3,
        )

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=model or "gemini-3.6-flash",
            google_api_key=api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"),
            temperature=0.3,
        )

    raise ValueError(f"Unknown provider for _build_model: {provider}")


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