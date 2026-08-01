import os
from llm.providers import call_llm
from guardrails.hooks import before_agent_hook, after_agent_hook
from observability.tracing import trace_llm_call


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


@trace_llm_call("newsana.explain")
def explain(
    query: str,
    retrieved_articles: list,
    sentiment: dict,
    outcome: dict,
    provider: str = "local",
    llm_model: str = None,
    api_key: str = None,
) -> dict:
    """
    Full guardrailed explanation pipeline.

    Returns:
        {
            "text": str,
            "provider_used": str,
            "cost_usd": float,
            "latency_ms": int,
            "hitl_required": bool,
            "blocked": bool,
            "blocked_reason": str | None,
        }
    """
    # ── Before-agent hook ──────────────────────────────────────────────────
    pre = before_agent_hook(query, provider)
    if not pre["allowed"]:
        return {"text": f"Blocked: {pre['reason']}", "provider_used": None,
                "cost_usd": 0.0, "latency_ms": 0, "hitl_required": False,
                "blocked": True, "blocked_reason": pre["reason"]}

    if pre["requires_human"]:
        return {"text": "This request requires human approval before proceeding.",
                "provider_used": None, "cost_usd": 0.0, "latency_ms": 0,
                "hitl_required": True, "blocked": False, "blocked_reason": None}

    sanitized_query = pre["sanitized_query"]
    prompt = _build_prompt(sanitized_query, retrieved_articles, sentiment, outcome)

    # ── LLM call with fallback chain ────────────────────────────────────────
    result = call_llm(prompt, user_provider=provider, user_model=llm_model,
                       user_key=api_key, max_tokens=300)

    # ── After-agent hook ────────────────────────────────────────────────────
    post = after_agent_hook(result["text"], result.get("provider_used"))

    return {
        "text": post["final_text"],
        "provider_used": result["provider_used"],
        "model_used": result["model_used"],
        "cost_usd": result["cost_usd"],
        "latency_ms": result["latency_ms"],
        "fallback_hops": result["fallback_hops"],
        "hitl_required": False,
        "blocked": not post["allowed"],
        "blocked_reason": post["reason"] if not post["allowed"] else None,
        "pii_redacted": pre.get("pii_found", []),
    }