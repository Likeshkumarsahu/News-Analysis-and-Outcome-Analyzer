from observability.tracing import trace_llm_call
from guardrails.graph import get_guardrail_graph


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
    thread_id: str = "default",
) -> dict:
    """
    Runs the LangGraph guardrail pipeline: before-hook → (HITL interrupt) →
    LangChain fallback-chain LLM call → after-hook.

    `thread_id` scopes the graph's checkpointer so a paused HITL query can be
    resumed later by the same conversation/session.
    """
    prompt = _build_prompt(query, retrieved_articles, sentiment, outcome)
    graph = get_guardrail_graph()

    initial_state = {
        "query": query, "prompt": prompt, "provider": provider,
        "llm_model": llm_model, "api_key": api_key,
        "sanitized_query": None, "pii_found": [], "blocked": False,
        "blocked_reason": None, "hitl_required": False,
        "llm_result": None, "final_text": None,
    }

    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke(initial_state, config=config)

    if result.get("hitl_required"):
        return {"text": "This request requires human approval before proceeding.",
                "provider_used": None, "cost_usd": 0.0, "latency_ms": 0,
                "hitl_required": True, "blocked": False, "blocked_reason": None,
                "pii_redacted": []}

    if result.get("blocked"):
        return {"text": result.get("final_text") or f"Blocked: {result.get('blocked_reason')}",
                "provider_used": None, "cost_usd": 0.0, "latency_ms": 0,
                "hitl_required": False, "blocked": True,
                "blocked_reason": result.get("blocked_reason"), "pii_redacted": []}

    llm_result = result.get("llm_result") or {}
    return {
        "text": result.get("final_text", ""),
        "provider_used": llm_result.get("provider_used"),
        "model_used": llm_result.get("model_used"),
        "cost_usd": llm_result.get("cost_usd", 0.0),
        "latency_ms": llm_result.get("latency_ms", 0),
        "fallback_hops": llm_result.get("fallback_hops", 0),
        "hitl_required": False,
        "blocked": False,
        "blocked_reason": None,
        "pii_redacted": result.get("pii_found", []),
    }


def resume_hitl(thread_id: str, approved: bool) -> dict:
    """
    Call this from a new /api/hitl/resume endpoint after a human reviews
    a paused query, to continue the graph past the interrupt() point.
    """
    from langgraph.types import Command
    graph = get_guardrail_graph()
    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke(Command(resume={"approved": approved}), config=config)

    if result.get("blocked"):
        return {"text": result.get("final_text"), "blocked": True,
                "blocked_reason": result.get("blocked_reason")}

    llm_result = result.get("llm_result") or {}
    return {"text": result.get("final_text", ""), "blocked": False,
            "provider_used": llm_result.get("provider_used"),
            "cost_usd": llm_result.get("cost_usd", 0.0)}