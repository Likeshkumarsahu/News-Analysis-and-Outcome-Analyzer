"""
observability/tracing.py
=========================
Provides `trace_llm_call`, a decorator factory used to wrap LLM-calling
functions (see models/llm_explainer.py::explain) with a named trace span.

Behavior:
- If LANGSMITH_API_KEY is set (and the `langsmith` package is importable),
  spans are reported to LangSmith via its `traceable` decorator, so you get
  full input/output/latency tracing in the LangSmith dashboard.
- If it's not configured, or `langsmith` fails to import for any reason,
  this falls back to a lightweight local logger instead of crashing the
  app — tracing is observability, it should never be a hard dependency
  for the request to succeed.

Usage:
    from observability.tracing import trace_llm_call

    @trace_llm_call("newsana.explain")
    def explain(...):
        ...
"""

import functools
import logging
import os
import time

logger = logging.getLogger("newsana.observability")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("[trace] %(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)

_LANGSMITH_ENABLED = False
_langsmith_traceable = None

if os.environ.get("LANGSMITH_API_KEY") or os.environ.get("LANGCHAIN_API_KEY"):
    try:
        from langsmith import traceable as _langsmith_traceable  # noqa: N812
        _LANGSMITH_ENABLED = True
    except Exception as exc:  # pragma: no cover - defensive import guard
        logger.warning("LangSmith is configured but failed to import (%s); "
                        "falling back to local trace logging.", exc)
        _LANGSMITH_ENABLED = False


# In-memory ring buffer of recent traces, useful for a debug endpoint or
# for /api/status to report basic call health without needing LangSmith.
_RECENT_TRACES = []
_MAX_RECENT_TRACES = 50


def _record_local_trace(span_name, func_name, duration_ms, success, error=None):
    entry = {
        "span": span_name,
        "function": func_name,
        "duration_ms": round(duration_ms, 2),
        "success": success,
        "error": str(error) if error else None,
        "ts": time.time(),
    }
    _RECENT_TRACES.append(entry)
    if len(_RECENT_TRACES) > _MAX_RECENT_TRACES:
        _RECENT_TRACES.pop(0)
    return entry


def get_recent_traces():
    """Returns the most recent local trace entries (newest last)."""
    return list(_RECENT_TRACES)


def _local_trace_decorator(span_name):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start) * 1000
                _record_local_trace(span_name, func.__name__, duration_ms, True)
                logger.info("%s -> %s ok in %.1fms", span_name, func.__name__, duration_ms)
                return result
            except Exception as exc:
                duration_ms = (time.perf_counter() - start) * 1000
                _record_local_trace(span_name, func.__name__, duration_ms, False, exc)
                logger.error("%s -> %s failed after %.1fms: %s",
                             span_name, func.__name__, duration_ms, exc)
                raise
        return wrapper
    return decorator


def trace_llm_call(span_name):
    """
    Decorator factory: @trace_llm_call("some.span.name")

    Wraps a function with a named trace span. Uses LangSmith when
    LANGSMITH_API_KEY / LANGCHAIN_API_KEY is set and the langsmith package
    is available; otherwise records lightweight local traces (visible via
    get_recent_traces()) and never blocks the wrapped call from running.
    """
    if _LANGSMITH_ENABLED and _langsmith_traceable is not None:
        try:
            return _langsmith_traceable(name=span_name)
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.warning("Failed to build LangSmith traceable for %s (%s); "
                            "using local tracing instead.", span_name, exc)
    return _local_trace_decorator(span_name)