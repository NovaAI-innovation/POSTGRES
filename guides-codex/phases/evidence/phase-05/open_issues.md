# Open Issues

1. Token estimation uses a lightweight word-based approximation; tokenizer-specific budgeting can be added later.
2. Compression and conflict subject extraction use heuristic keys and should be hardened with schema-aware fact extraction.
3. Context assembly currently relies on retrieval payload fields and does not yet include conversation role weighting.
