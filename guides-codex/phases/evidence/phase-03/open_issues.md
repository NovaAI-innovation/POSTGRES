# Open Issues

1. Ingestion currently runs inline in API process; async queue/worker deployment path is deferred.
2. Extraction/classification/scoring heuristics are deterministic and simple; model-driven extraction is deferred.
3. Dedup currently uses in-memory repository state; persistent DB-backed dedup index is pending.
