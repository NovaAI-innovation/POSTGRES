# Open Issues

1. Retrieval currently reads from in-memory repository; DB-native helper function and vector index plans are deferred.
2. Hybrid score weights are static constants and not yet tuned by offline eval metrics.
3. Retrieval does not yet include full-text index-backed keyword ranking (planned when DB adapter is added).
