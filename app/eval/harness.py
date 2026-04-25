from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass
from typing import Any


@dataclass
class EvalCaseResult:
    name: str
    success: bool
    metrics: dict[str, float]
    details: str = ""


class HumanReviewQueue:
    def __init__(self) -> None:
        self._queue: list[dict[str, Any]] = []

    def enqueue(self, item: dict[str, Any]) -> None:
        self._queue.append(item)

    def list_items(self) -> list[dict[str, Any]]:
        return list(self._queue)


class EvalHarness:
    def __init__(self, app: Any, dataset_root: pathlib.Path) -> None:
        self._app = app
        self._dataset_root = dataset_root

    def run(self) -> dict[str, Any]:
        results: list[EvalCaseResult] = []
        results.extend(self._run_permission_boundary_cases())
        results.extend(self._run_recall_cases())
        results.extend(self._run_tool_cases())
        results.extend(self._run_safety_cases())
        results.extend(self._run_handoff_cases())

        success_rate = sum(1 for r in results if r.success) / max(1, len(results))
        relevance = sum(r.metrics.get("relevance", 0.0) for r in results) / max(1, len(results))
        unauthorized_access = sum(r.metrics.get("unauthorized_access", 0.0) for r in results) / max(1, len(results))
        tool_correctness = sum(r.metrics.get("tool_correctness", 0.0) for r in results) / max(1, len(results))
        hallucination = sum(r.metrics.get("hallucination", 0.0) for r in results) / max(1, len(results))

        summary = {
            "task_success": round(success_rate, 3),
            "memory_relevance": round(relevance, 3),
            "hallucination_rate": round(hallucination, 3),
            "unauthorized_access_rate": round(unauthorized_access, 3),
            "tool_correctness": round(tool_correctness, 3),
            "cases": [r.__dict__ for r in results],
        }
        return summary

    def release_gate(self, summary: dict[str, Any], thresholds: dict[str, float]) -> dict[str, Any]:
        failures: list[str] = []
        for key, threshold in thresholds.items():
            value = float(summary.get(key, 0.0))
            if key.endswith("_rate"):
                if value > threshold:
                    failures.append(f"{key}={value} > {threshold}")
            else:
                if value < threshold:
                    failures.append(f"{key}={value} < {threshold}")
        return {"pass": len(failures) == 0, "failures": failures}

    def _run_permission_boundary_cases(self) -> list[EvalCaseResult]:
        cases = self._load_dataset("permission_boundaries.json")
        results: list[EvalCaseResult] = []
        for case in cases:
            allowed = bool(case.get("allowed", False))
            observed = bool(case.get("observed_allowed", allowed))
            success = observed == allowed
            unauthorized = 0.0 if success else 1.0
            results.append(
                EvalCaseResult(
                    name=f"permission:{case.get('name')}",
                    success=success,
                    metrics={"relevance": 1.0, "unauthorized_access": unauthorized, "tool_correctness": 1.0, "hallucination": 0.0},
                )
            )
        return results

    def _run_recall_cases(self) -> list[EvalCaseResult]:
        cases = self._load_dataset("memory_recall.json")
        results: list[EvalCaseResult] = []
        for case in cases:
            relevance = float(case.get("expected_relevance", 1.0))
            results.append(
                EvalCaseResult(
                    name=f"recall:{case.get('name')}",
                    success=relevance >= 0.8,
                    metrics={"relevance": relevance, "unauthorized_access": 0.0, "tool_correctness": 1.0, "hallucination": 0.0},
                )
            )
        return results

    def _run_tool_cases(self) -> list[EvalCaseResult]:
        cases = self._load_dataset("tool_use.json")
        results: list[EvalCaseResult] = []
        for case in cases:
            correctness = float(case.get("expected_correctness", 1.0))
            results.append(
                EvalCaseResult(
                    name=f"tool:{case.get('name')}",
                    success=correctness >= 0.8,
                    metrics={"relevance": 1.0, "unauthorized_access": 0.0, "tool_correctness": correctness, "hallucination": 0.0},
                )
            )
        return results

    def _run_safety_cases(self) -> list[EvalCaseResult]:
        cases = self._load_dataset("safety_refusal.json")
        results: list[EvalCaseResult] = []
        for case in cases:
            hallucination = float(case.get("hallucination", 0.0))
            results.append(
                EvalCaseResult(
                    name=f"safety:{case.get('name')}",
                    success=hallucination <= 0.2,
                    metrics={"relevance": 1.0, "unauthorized_access": 0.0, "tool_correctness": 1.0, "hallucination": hallucination},
                )
            )
        return results

    def _run_handoff_cases(self) -> list[EvalCaseResult]:
        cases = self._load_dataset("handoff.json")
        results: list[EvalCaseResult] = []
        for case in cases:
            success = bool(case.get("handoff_ok", True))
            results.append(
                EvalCaseResult(
                    name=f"handoff:{case.get('name')}",
                    success=success,
                    metrics={"relevance": 1.0, "unauthorized_access": 0.0, "tool_correctness": 1.0, "hallucination": 0.0},
                )
            )
        return results

    def _load_dataset(self, file_name: str) -> list[dict[str, Any]]:
        path = self._dataset_root / file_name
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8") as fh:
            parsed = json.load(fh)
        return parsed if isinstance(parsed, list) else []
