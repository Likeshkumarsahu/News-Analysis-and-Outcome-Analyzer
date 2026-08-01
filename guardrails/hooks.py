import re

# Queries that must pause for human approval before running (destructive/sensitive intents)
HITL_TRIGGER_PATTERNS = [
    r"\bdelete\b", r"\bdrop\b", r"\bexecute\b.*\bcommand\b",
    r"\bshut\s*down\b", r"\bformat\b.*\bdrive\b",
]

BLOCKED_PATTERNS = [
    r"\bignore\s+(all\s+)?previous\s+instructions\b",
    r"\bsystem\s*prompt\b.*\breveal\b",
]


def before_agent_hook(query: str, provider: str) -> dict:
    """
    Runs BEFORE any LLM/agent call.
    Returns {"allowed": bool, "reason": str, "requires_human": bool, "sanitized_query": str}
    """
    q_lower = query.lower()

    for pat in BLOCKED_PATTERNS:
        if re.search(pat, q_lower):
            return {"allowed": False, "reason": "Prompt injection pattern detected.",
                     "requires_human": False, "sanitized_query": query}

    for pat in HITL_TRIGGER_PATTERNS:
        if re.search(pat, q_lower):
            return {"allowed": True, "reason": "Sensitive intent — human approval required.",
                     "requires_human": True, "sanitized_query": query}

    if len(query) > 2000:
        return {"allowed": False, "reason": "Query exceeds maximum length (2000 chars).",
                 "requires_human": False, "sanitized_query": query}

    from guardrails.pii import redact_pii
    pii_result = redact_pii(query)

    return {"allowed": True, "reason": "OK", "requires_human": False,
             "sanitized_query": pii_result["text"], "pii_found": pii_result["found"]}


def after_agent_hook(output_text: str, provider: str) -> dict:
    """
    Runs AFTER any LLM/agent call, before returning to the user.
    Checks for leaked system prompt, empty output, or obviously broken responses.
    Returns {"allowed": bool, "reason": str, "final_text": str}
    """
    if not output_text or len(output_text.strip()) < 3:
        return {"allowed": False, "reason": "Empty or degenerate output.",
                 "final_text": "The model returned an empty response. Please retry."}

    leak_markers = ["you are a news analyst", "system prompt:", "<|system|>"]
    lowered = output_text.lower()
    for marker in leak_markers:
        if marker in lowered and len(output_text) < 60:
            return {"allowed": False, "reason": "Possible system prompt leak.",
                     "final_text": "Response filtered for safety. Please retry."}

    return {"allowed": True, "reason": "OK", "final_text": output_text}