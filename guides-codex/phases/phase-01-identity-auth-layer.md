---
phase_id: "1"
phase_key: "identity-auth-layer"
phase_name: "Identity and Auth Layer"
source_plan: "guides-codex/production_agent_layers_implementation_plan.md"
depends_on_phase_ids: ["0"]
execution_mode: "deterministic"
---

# Phase 1 - Identity and Auth Layer Agent Guide

## Goal

Ensure every request is tied to a known agent, user, tenant, or service identity.

## Required Inputs

- Source plan: guides-codex/production_agent_layers_implementation_plan.md
- Phase dependencies marked complete in prior phase guides.
- Service/API codebase access and migration tooling access.
- Test environment with PostgreSQL and pgvector available.

## Build Checklist

- [ ] Add identity model: tenant_id, user_id, agent_id, service_client_id.
- [ ] Add API auth: JWT or signed service token; API key fallback for internal/dev only.
- [ ] Add request context middleware: principal, agent_id, tenant_id, request_id.
- [ ] Add secret handling: secret manager, key rotation, no secrets in logs.
- [ ] Emit auth audit events: success, failure, expired token, invalid identity.

## Required Deliverables

- [ ] Auth middleware.
- [ ] Identity context object.
- [ ] Credential issuance process.
- [ ] Auth audit logs.

## Verification Gates

- [ ] Every memory/tool request has verified identity.
- [ ] Unauthorized requests are rejected before business logic.
- [ ] Automated tests or scripted checks exist for all new critical paths.
- [ ] Evidence artifacts are produced under guides-codex/phases/evidence/phase-01/.

## Evidence Contract

Produce the following machine-readable artifacts:

- implementation_summary.md: concise scope and final architecture decisions.
- changed_files.txt: newline-separated absolute or repo-relative paths changed for this phase.
- test_results.txt: command list and pass/fail output.
- open_issues.md: unresolved risks, deferred work, and compensating controls.

## Handoff To Next Phase

- [ ] All verification gates are checked.
- [ ] API/schema contracts touched in this phase are documented in implementation_summary.md.
- [ ] Backward compatibility impact (if any) is listed.
- [ ] Next phase prerequisites are explicitly satisfied.

## Agent Execution Prompt Template

Use this prompt when delegating this phase to another AI agent:

1. "Implement exactly Phase 1 (Identity and Auth Layer) from guides-codex/production_agent_layers_implementation_plan.md."
2. "Follow the checklist and deliverables in this file; do not skip verification gates."
3. "Write evidence artifacts under guides-codex/phases/evidence/phase-01/."
4. "Return: summary, changed files, test commands run, and gate status."
