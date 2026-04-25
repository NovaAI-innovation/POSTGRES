# Memory Pipeline Contracts (Phases 3-5)

## Ingestion API

- `POST /memory/ingest`
- Input: `raw_content` (or `content`), `scope`, optional `group_id`, `source_ref`, `metadata`.
- Output: `inserted`, `reason`, `debug`, `memory`.

## Retrieval API

- `POST /memory/search`
- Input: `query`, optional `filters`, `limit`, `debug`.
- Output: ranked `items` with `source_label`, scope, confidence, score, and optional debug components.

## Context Assembly API

- `POST /context/assemble`
- Input: `query`, optional retrieval filters/limit/debug, optional `budgets`, `tool_results`, `history`.
- Output: `context` with memory/tool/history blocks, token usage, and surfaced conflicts.
