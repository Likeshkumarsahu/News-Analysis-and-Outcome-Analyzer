import os
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool

from retrieval.search import search
from models.sentiment import analyze_sentiment
from models.outcome import predict_outcome
from llm.providers import _build_model

# Used only when the caller doesn't pass a provider/model (e.g. no selection
# made yet, or Local/Ollama which needs no explicit model from the user).
DEFAULT_PROVIDER = os.getenv("CREW_PROVIDER", "local")
DEFAULT_MODEL    = os.getenv("CREW_MODEL", "llama3.2:3b")


@tool
def news_search_tool(query: str) -> str:
    """Search for relevant news articles from the database."""
    results = search(query, top_k=5)
    if not results:
        return f"No articles found for query: {query}"
    return "\n\n".join(
        f"Article {i}:\n  Title: {r['title']}\n  Source: {r['source']}\n"
        f"  Summary: {r['text'][:300]}\n  Score: {r['score']:.3f}"
        for i, r in enumerate(results, 1)
    )


@tool
def sentiment_tool(text: str) -> str:
    """Analyze sentiment of a news text: POSITIVE, NEGATIVE, or NEUTRAL."""
    result = analyze_sentiment(text)
    return f"Sentiment: {result['label'].upper()}\nConfidence: {result['confidence']:.1%}"


@tool
def impact_tool(text: str) -> str:
    """Predict impact level of news: HIGH, MEDIUM, or LOW."""
    result = predict_outcome(text)
    return (f"Impact: {result['impact']}\nConfidence: {result['confidence']:.1%}\n"
            f"Signals: {', '.join(result['matched']) if result['matched'] else 'none'}")


class CrewState(TypedDict):
    query: str
    provider: str
    llm_model: str
    api_key: str
    analysis: str
    predictions: str
    critique: str
    final_summary: str


_SYSTEM_PROMPTS = {
    "analyst": (
        "You are a Senior News Analyst. You have exactly two tools available, named "
        "`news_search_tool` and `sentiment_tool`. Use them to find relevant articles and "
        "assess tone, then summarize the current situation factually in 3-4 sentences, "
        "listing key facts and entities. Only call tools by these exact names — "
        "never invent or guess a tool name that isn't listed here."
    ),
    "predictor": (
        "You are a Strategic Intelligence Analyst. You have exactly one tool available, "
        "named `impact_tool`. Call it at most once to assess severity, then — using your "
        "own reasoning, not a tool — predict 3 short-term outcomes (1-4 weeks) and 2 "
        "long-term consequences (3-6 months), and rate overall severity as "
        "LOW/MEDIUM/HIGH/CRITICAL. Only call a tool by the exact name `impact_tool` — "
        "never invent a different tool name such as one that merely describes what you "
        "are about to do."
    ),
    "critic": (
        "You are an Editorial Fact Checker. You have exactly one tool available, named "
        "`news_search_tool`. Review the analysis and predictions given to you, use the "
        "tool only if you need to check a corroborating source, flag bias or gaps, and "
        "write a balanced executive summary under 150 words. Only call tools by their "
        "exact name — never invent a tool name that isn't listed here."
    ),
}

_AGENT_TOOLS = {
    "analyst":   [news_search_tool, sentiment_tool],
    "predictor": [impact_tool],
    "critic":    [news_search_tool],
}

# Cached per (provider, model, has_key) so repeat requests with the same
# selection don't rebuild the LangChain client every time — but a different
# provider/model picked on the website builds (and caches) its own set.
_AGENT_CACHE = {}


def _get_agents(provider: str, model: str, api_key: str = None) -> dict:
    cache_key = (provider, model, bool(api_key))
    if cache_key in _AGENT_CACHE:
        return _AGENT_CACHE[cache_key]

    llm = _build_model(provider, model, api_key)
    bundle = {
        "llm": llm,
        **{
            name: create_react_agent(llm, _AGENT_TOOLS[name], prompt=_SYSTEM_PROMPTS[name])
            for name in ("analyst", "predictor", "critic")
        },
    }
    _AGENT_CACHE[cache_key] = bundle
    return bundle


def _safe_invoke(bundle: dict, name: str, user_message: str) -> str:
    """
    Runs the named agent's tool-calling loop. Some smaller/weaker models
    (e.g. Groq's llama-3.1-8b-instant) occasionally hallucinate a tool name
    that isn't actually bound to the request — Groq validates this strictly
    and raises a 400, which would otherwise crash the whole /api/crew
    request. If that happens, retry once as a plain direct answer with no
    tool-calling at all, so the pipeline still produces output.
    """
    agent = bundle[name]
    try:
        result = agent.invoke({"messages": [("user", user_message)]})
        return result["messages"][-1].content
    except Exception as e:
        err = str(e)
        is_tool_error = "tool" in err.lower() and (
            "not in request.tools" in err or "tool_use_failed" in err or "validation failed" in err
        )
        if not is_tool_error:
            raise  # a real failure (bad key, network, etc.) — don't mask it

        print(f"⚠️ {name} agent hit an invalid tool call ({e}); "
              f"retrying as a direct (no-tool) answer.")
        try:
            direct = bundle["llm"].invoke([
                ("system", "Answer directly using only your own reasoning. "
                           "Do not attempt to call any tool or function."),
                ("user", user_message),
            ])
            return direct.content
        except Exception as e2:
            return f"[{name} agent failed even without tools: {e2}]"


def analyst_node(state: CrewState) -> CrewState:
    bundle = _get_agents(state["provider"], state["llm_model"], state.get("api_key"))
    state["analysis"] = _safe_invoke(
        bundle, "analyst", f"Analyze the news for: {state['query']}"
    )
    return state


def predictor_node(state: CrewState) -> CrewState:
    bundle = _get_agents(state["provider"], state["llm_model"], state.get("api_key"))
    msg = f"Query: {state['query']}\n\nAnalyst's findings:\n{state['analysis']}\n\nPredict outcomes."
    state["predictions"] = _safe_invoke(bundle, "predictor", msg)
    return state


def critic_node(state: CrewState) -> CrewState:
    bundle = _get_agents(state["provider"], state["llm_model"], state.get("api_key"))
    msg = (f"Query: {state['query']}\n\nAnalysis:\n{state['analysis']}\n\n"
           f"Predictions:\n{state['predictions']}\n\nReview and summarize.")
    critique = _safe_invoke(bundle, "critic", msg)
    state["critique"] = critique
    state["final_summary"] = critique
    return state


def build_news_crew_graph():
    graph = StateGraph(CrewState)
    graph.add_node("analyst", analyst_node)
    graph.add_node("predictor", predictor_node)
    graph.add_node("critic", critic_node)

    graph.set_entry_point("analyst")
    graph.add_edge("analyst", "predictor")
    graph.add_edge("predictor", "critic")
    graph.add_edge("critic", END)

    return graph.compile()


_compiled_crew = None


def run_news_crew(query: str, provider: str = None, llm_model: str = None, api_key: str = None) -> dict:
    """
    Run the 3-node LangGraph multi-agent pipeline (Analyst → Predictor → Critic),
    using whichever provider + model the user picked in the website's provider
    selector (falls back to CREW_PROVIDER/CREW_MODEL env vars if none was
    passed — e.g. Local/Ollama, which the frontend never sends a model for).
    """
    global _compiled_crew
    if _compiled_crew is None:
        _compiled_crew = build_news_crew_graph()

    provider  = provider or DEFAULT_PROVIDER
    llm_model = llm_model or DEFAULT_MODEL

    print(f"\n🤖 Starting LangGraph multi-agent pipeline for: '{query}' "
          f"(provider={provider}, model={llm_model})")

    result = _compiled_crew.invoke({
        "query": query, "provider": provider, "llm_model": llm_model, "api_key": api_key,
        "analysis": "", "predictions": "", "critique": "", "final_summary": "",
    })

    return {
        "query": query,
        "provider": provider,
        "model": llm_model,
        "analysis": result["analysis"],
        "predictions": result["predictions"],
        "critique": result["critique"],
        "final_summary": result["final_summary"],
    }