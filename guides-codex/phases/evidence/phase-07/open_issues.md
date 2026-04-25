# Open Issues

1. Tracing currently stores spans in-memory; no external OTLP exporter has been configured.
2. Metrics are in-memory snapshots and not yet pushed to Prometheus/OpenTelemetry backends.
3. Dashboard/alert files are templates; platform-specific deployment wiring is deferred.
