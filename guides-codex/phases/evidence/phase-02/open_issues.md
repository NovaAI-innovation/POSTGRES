# Open Issues

1. Policy decision logs are emitted to structured logs; DB persistence and analytics views are deferred.
2. Group and override data stores are in-memory for this phase; PostgreSQL-backed adapters are pending subsequent phase implementation.
3. Delegation policy check exists in engine but delegation endpoint/orchestration is deferred to later phases.
