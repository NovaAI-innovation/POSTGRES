from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Span:
    name: str
    start_ms: int
    end_ms: int | None = None
    attrs: dict[str, Any] = field(default_factory=dict)


@dataclass
class Trace:
    trace_id: str
    request_id: str
    spans: list[Span] = field(default_factory=list)


class Tracer:
    def __init__(self) -> None:
        self._traces: dict[str, Trace] = {}

    def start_trace(self, request_id: str) -> Trace:
        trace = Trace(trace_id=str(uuid.uuid4()), request_id=request_id)
        self._traces[trace.trace_id] = trace
        return trace

    def start_span(self, trace: Trace, name: str, attrs: dict[str, Any] | None = None) -> Span:
        span = Span(name=name, start_ms=int(time.time() * 1000), attrs=attrs or {})
        trace.spans.append(span)
        return span

    def end_span(self, span: Span, attrs: dict[str, Any] | None = None) -> None:
        span.end_ms = int(time.time() * 1000)
        if attrs:
            span.attrs.update(attrs)

    def export_trace(self, trace_id: str) -> dict[str, Any] | None:
        trace = self._traces.get(trace_id)
        if not trace:
            return None
        return {
            "trace_id": trace.trace_id,
            "request_id": trace.request_id,
            "spans": [
                {
                    "name": s.name,
                    "start_ms": s.start_ms,
                    "end_ms": s.end_ms,
                    "duration_ms": (s.end_ms - s.start_ms) if s.end_ms else None,
                    "attrs": s.attrs,
                }
                for s in trace.spans
            ],
        }

    def list_traces(self, limit: int = 50) -> list[dict[str, Any]]:
        traces = list(self._traces.values())[-limit:]
        return [self.export_trace(t.trace_id) for t in traces if self.export_trace(t.trace_id) is not None]
