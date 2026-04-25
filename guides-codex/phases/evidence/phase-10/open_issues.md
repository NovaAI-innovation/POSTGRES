# Open Issues

1. Task queue is in-memory; distributed queue backend and durable worker recovery are deferred.
2. Lock manager is process-local and does not provide cross-instance distributed locking.
3. Dead-letter replay tooling is not yet implemented.
