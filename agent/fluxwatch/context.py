from __future__ import annotations

import uuid
from contextvars import ContextVar

_trace_id: ContextVar[str] = ContextVar("trace_id", default="")
_span_id: ContextVar[str] = ContextVar("span_id", default="")
_parent_trace_id: ContextVar[str] = ContextVar("parent_trace_id", default="")
_parent_span_id: ContextVar[str] = ContextVar("parent_span_id", default="")


def get_trace_id() -> str:
    tid = _trace_id.get()
    if not tid:
        tid = uuid.uuid4().hex
        _trace_id.set(tid)
    return tid


def get_span_id() -> str:
    sid = _span_id.get()
    if not sid:
        sid = uuid.uuid4().hex[:16]
        _span_id.set(sid)
    return sid


def new_span(name: str | None = None) -> SpanContext:
    parent_trace = _trace_id.get() or get_trace_id()
    parent_span = _span_id.get()
    span_id = uuid.uuid4().hex[:16]
    _trace_id.set(parent_trace)
    _parent_trace_id.set(parent_trace)
    _parent_span_id.set(parent_span)
    _span_id.set(span_id)
    return SpanContext(trace_id=parent_trace, span_id=span_id, name=name)


def reset_context() -> None:
    _trace_id.set("")
    _span_id.set("")
    _parent_trace_id.set("")
    _parent_span_id.set("")


def set_trace_context(trace_id: str, span_id: str) -> None:
    _trace_id.set(trace_id)
    _span_id.set(span_id)


class SpanContext:
    __slots__ = ("trace_id", "span_id", "name", "_token_trace", "_token_span", "_token_parent_trace", "_token_parent_span")

    def __init__(self, trace_id: str, span_id: str, name: str | None = None) -> None:
        self.trace_id = trace_id
        self.span_id = span_id
        self.name = name
        self._token_trace = None
        self._token_span = None
        self._token_parent_trace = None
        self._token_parent_span = None

    def __enter__(self) -> SpanContext:
        self._token_trace = _trace_id.set(self.trace_id)
        self._token_span = _span_id.set(self.span_id)
        return self

    def __exit__(self, *args: object) -> None:
        if self._token_trace is not None:
            _trace_id.reset(self._token_trace)
        if self._token_span is not None:
            _span_id.reset(self._token_span)

    def child(self, name: str | None = None) -> SpanContext:
        child_span_id = uuid.uuid4().hex[:16]
        return SpanContext(trace_id=self.trace_id, span_id=child_span_id, name=name)

    def to_headers(self) -> dict[str, str]:
        return {
            "X-Trace-Id": self.trace_id,
            "X-Span-Id": self.span_id,
        }

    @classmethod
    def from_headers(cls, headers: dict[str, str]) -> SpanContext:
        trace_id = headers.get("X-Trace-Id", "")
        span_id = headers.get("X-Span-Id", "")
        if not trace_id:
            trace_id = uuid.uuid4().hex
        if not span_id:
            span_id = uuid.uuid4().hex[:16]
        return cls(trace_id=trace_id, span_id=span_id)
