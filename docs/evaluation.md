# Evaluation Layer (Phase 8)

- Eval datasets are in `eval/datasets/`:
  - memory recall
  - permission boundaries
  - tool use
  - safety/refusal
  - handoff
- Eval harness: `app/eval/harness.py`.
- CLI regression entrypoint: `python -m app.eval.run` (also `scripts/run_regression.ps1`).
- Release thresholds: `eval/release_gates.json`.
- Golden trace baseline: `eval/golden_traces/critical_workflow_trace.json`.
- Human review queue endpoint: `GET /eval/review-queue`.
