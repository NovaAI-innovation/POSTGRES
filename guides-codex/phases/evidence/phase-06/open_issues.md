# Open Issues

1. Tool audit records are in-memory; DB persistence adapters for `tool_calls` and `tool_approvals` are not wired yet.
2. Tool handler execution currently uses in-process callables; external process/container isolation is deferred.
3. Approval reason taxonomy is basic and should be expanded for operator workflows.
