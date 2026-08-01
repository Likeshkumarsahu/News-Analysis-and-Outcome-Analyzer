#Logfire + LangSmith wiring

import os
import functools
import time

_logfire_enabled  = bool(os.getenv("LOGFIRE_TOKEN"))
_langsmith_enabled = bool(os.getenv("LANGSMITH_API_KEY"))

if _logfire_enabled:
    import logfire
    logfire.configure(token=os.getenv("LOGFIRE_TOKEN"))

if _langsmith_enabled:
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ.setdefault("LANGCHAIN_PROJECT", os.getenv("LANGSMITH_PROJECT", "newsana"))
    os.environ.setdefault("LANGCHAIN_API_KEY", os.getenv("LANGSMITH_API_KEY", ""))
    from langsmith import traceable
else:
    def traceable(*dargs, **dkwargs):
        def deco(fn):
            return fn
        return deco


def trace_llm_call(name: str):
    """Decorator: wraps an LLM call function with Logfire span + LangSmith trace."""
    def decorator(fn):
        traced_fn = traceable(name=name)(fn) if _langsmith_enabled else fn

        @functools.wraps(traced_fn)
        def wrapper(*args, **kwargs):
            start = time.time()
            if _logfire_enabled:
                with logfire.span(name, **{k: v for k, v in kwargs.items() if isinstance(v, (str, int, float, bool))}):
                    result = traced_fn(*args, **kwargs)
                    logfire.info(f"{name} completed", duration_ms=int((time.time()-start)*1000))
                    return result
            return traced_fn(*args, **kwargs)
        return wrapper
    return decorator