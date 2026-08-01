import os
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool

from retrieval.search import search
from models.sentiment import analyze_sentiment
from models.outcome import predict_outcome
from llm.providers import _build_model

MODEL_PROVIDER = os.getenv("CREW_PROVIDER", "local")
MODEL_NAME     = os.getenv("CREW_MODEL", "llama3.2:3b")


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
    analysis: str
    predictions: str
    critique: str
    final_summary: str


def _make_agent(system_prompt: str, tools: list):
    llm = _build_model(MODEL_PROVIDER, MODEL_NAME)
    return create_react_agent(llm, tools, prompt=system_prompt)


_analyst_agent = _make_agent(
    "You are a Senior News Analyst. Use the news search and sentiment tools to "
    "find relevant articles and summarize the current situation factually in 3-4 sentences, "
    "listing key facts and entities.",
    [news_search_tool, sentiment_tool],
)

_predictor_agent = _make_agent(
    "You are a Strategic Intelligence Analyst. Given a news analysis, use the impact tool "
    "to assess severity, then predict 3 short-term outcomes (1-4 weeks) and 2 long-term "
    "consequences (3-6 months). Rate overall severity LOW/MEDIUM/HIGH/CRITICAL.",
    [impact_tool],
)

_critic_agent = _make_agent(
    "You are an Editorial Fact Checker. Review the analysis and predictions given to you. "
    "Search for corroborating sources if needed, flag bias or gaps, and write a balanced "
    "executive summary under 150 words.",
    [news_search_tool],
)


def analyst_node(state: CrewState) -> CrewState:
    result = _analyst_agent.invoke({"messages": [("user", f"Analyze the news for: {state['query']}")]})
    state["analysis"] = result["messages"][-1].content
    return state


def predictor_node(state: CrewState) -> CrewState:
    msg = f"Query: {state['query']}\n\nAnalyst's findings:\n{state['analysis']}\n\nPredict outcomes."
    result = _predictor_agent.invoke({"messages": [("user", msg)]})
    state["predictions"] = result["messages"][-1].content
    return state


def critic_node(state: CrewState) -> CrewState:
    msg = (f"Query: {state['query']}\n\nAnalysis:\n{state['analysis']}\n\n"
           f"Predictions:\n{state['predictions']}\n\nReview and summarize.")
    result = _critic_agent.invoke({"messages": [("user", msg)]})
    state["critique"] = result["messages"][-1].content
    state["final_summary"] = state["critique"]
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


def run_news_crew(query: str) -> dict:
    """
    Run the 3-node LangGraph multi-agent pipeline (Analyst → Predictor → Critic).
    Same return shape as the old CrewAI version, so server.py's /api/crew route
    doesn't need to change.
    """
    global _compiled_crew
    if _compiled_crew is None:
        _compiled_crew = build_news_crew_graph()

    print(f"\n🤖 Starting LangGraph multi-agent pipeline for: '{query}'")

    result = _compiled_crew.invoke({
        "query": query, "analysis": "", "predictions": "", "critique": "", "final_summary": "",
    })

    return {
        "query": query,
        "analysis": result["analysis"],
        "predictions": result["predictions"],
        "critique": result["critique"],
        "final_summary": result["final_summary"],
    }