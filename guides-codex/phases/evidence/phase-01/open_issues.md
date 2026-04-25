# Open Issues

1. Secret manager integration is represented by environment-based secret loading and rotation slots; external secret manager backend wiring is deferred.
2. Credential issuance exists as internal functions; external issuance endpoint/workflow is deferred pending operator controls.
3. Auth audit events are currently structured logs and are not yet persisted into the database tables.
