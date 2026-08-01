from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from langgraph.types import interrupt
from langgraph.checkpoint.memory import MemorySaver

from guardrails.pii import redact_pii
from llm.providers import call_llm
import re

HITL_TRIGGER_PATTERNS = [
    r"\bdelete\b", r"\bdrop\b", r"\bexecute\b.*\bcommand\b",
    r"\bshut\s*down\b", r"\bformat\b.*\bdrive\b",
]
BLOCKED_PATTERNS = [
    r"\bignore\s+(all\s+)?previous\s+instructions\b",
    r"\bsystem\s*prompt\b.*\breveal\b",
]


class GuardState(TypedDict):
    query: str
    prompt: str
    provider: str
    llm_model: Optional[str]
    api_key: Optional[str]
    sanitized_query: Optional[str]
    pii_found: list
    blocked: bool
    blocked_reason: Optional[str]
    hitl_required: bool
    llm_result: Optional[dict]
    final_text: Optional[str]


def before_hook_node(state: GuardState) -> GuardState:
    q_lower = state["query"].lower()

    for pat in BLOCKED_PATTERNS:
        if re.search(pat, q_lower):
            state["blocked"] = True
            state["blocked_reason"] = "Prompt injection pattern detected."
            return state

    if len(state["query"]) > 2000:
        state["blocked"] = True
        state["blocked_reason"] = "Query exceeds maximum length (2000 chars)."
        return state

    for pat in HITL_TRIGGER_PATTERNS:
        if re.search(pat, q_lower):
            state["hitl_required"] = True
            return state

    pii = redact_pii(state["query"])
    state["sanitized_query"] = pii["text"]
    state["pii_found"] = pii["found"]
    state["blocked"] = False
    return state


def hitl_node(state: GuardState) -> GuardState:
    """
    LangGraph human-in-the-loop pause. Execution stops here until the caller
    resumes the graph with Command(resume=<decision>).
    """
    decision = interrupt({
        "message": "This query matched a sensitive-intent pattern and requires human approval.",
        "query": state["query"],
    })
    # decision is whatever the resumer passes back, e.g. {"approved": True}
    if not decision or not decision.get("approved"):
        state["blocked"] = True
        state["blocked_reason"] = "Rejected by human reviewer."
    else:
        state["hitl_required"] = False
        state["sanitized_query"] = state["query"]
        state["pii_found"] = []
    return state


def llm_call_node(state: GuardState) -> GuardState:
    prompt = state["prompt"].replace(state["query"], state["sanitized_query"] or state["query"])
    result = call_llm(prompt, user_provider=state["provider"],
                       user_model=state.get("llm_model"), user_key=state.get("api_key"))
    state["llm_result"] = result
    return state


def after_hook_node(state: GuardState) -> GuardState:
    result = state["llm_result"] or {}
    text = result.get("text", "")

    if not text or len(text.strip()) < 3:
        state["blocked"] = True
        state["blocked_reason"] = "Empty or degenerate output."
        state["final_text"] = "The model returned an empty response. Please retry."
        return state

    leak_markers = ["you are a news analyst", "system prompt:", "<|system|>"]
    if any(m in text.lower() for m in leak_markers) and len(text) < 60:
        state["blocked"] = True
        state["blocked_reason"] = "Possible system prompt leak."
        state["final_text"] = "Response filtered for safety. Please retry."
        return state

    state["blocked"] = False
    state["final_text"] = text
    return state


def route_after_before(state: GuardState) -> str:
    if state.get("blocked"):
        return "end"
    if state.get("hitl_required"):
        return "hitl"
    return "llm_call"


def route_after_hitl(state: GuardState) -> str:
    return "end" if state.get("blocked") else "llm_call"


def build_guardrail_graph():
    graph = StateGraph(GuardState)
    graph.add_node("before_hook", before_hook_node)
    graph.add_node("hitl", hitl_node)
    graph.add_node("llm_call", llm_call_node)
    graph.add_node("after_hook", after_hook_node)

    graph.set_entry_point("before_hook")
    graph.add_conditional_edges("before_hook", route_after_before,
                                 {"end": END, "hitl": "hitl", "llm_call": "llm_call"})
    graph.add_conditional_edges("hitl", route_after_hitl,
                                 {"end": END, "llm_call": "llm_call"})
    graph.add_edge("llm_call", "after_hook")
    graph.add_edge("after_hook", END)

    checkpointer = MemorySaver()  # enables interrupt/resume across calls
    return graph.compile(checkpointer=checkpointer)


_compiled_graph = None


def get_guardrail_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_guardrail_graph()
    return _compiled_graph