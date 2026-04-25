from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any


@dataclass
class MetricPoint:
    value: float
    tags: dict[str, str]


class MetricsStore:
    def __init__(self) -> None:
        self._counters: dict[str, float] = defaultdict(float)
        self._timings: dict[str, list[MetricPoint]] = defaultdict(list)
        self._gauges: dict[str, float] = {}

    def inc(self, name: str, value: float = 1.0) -> None:
        self._counters[name] += value

    def observe_ms(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        self._timings[name].append(MetricPoint(value=value, tags=tags or {}))

    def set_gauge(self, name: str, value: float) -> None:
        self._gauges[name] = value

    def snapshot(self) -> dict[str, Any]:
        timings: dict[str, Any] = {}
        for key, points in self._timings.items():
            values = [p.value for p in points]
            if not values:
                continue
            timings[key] = {
                "count": len(values),
                "avg_ms": round(sum(values) / len(values), 2),
                "max_ms": round(max(values), 2),
            }
        return {
            "counters": dict(self._counters),
            "timings": timings,
            "gauges": dict(self._gauges),
        }
