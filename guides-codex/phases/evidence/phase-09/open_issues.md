# Open Issues

1. PII/secret detection is regex-based and should be augmented with stronger classifiers.
2. Retention enforcement is currently represented through metadata/expiry semantics and lacks background cleanup jobs.
3. Guardrail policy configuration is code-defined; dynamic tenant-level safety policy management is deferred.
