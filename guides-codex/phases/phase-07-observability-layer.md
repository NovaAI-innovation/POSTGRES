---
phase_id: "7"
phase_key: "observability-layer"
phase_name: "Observability Layer"
source_plan: "guides-codex/production_agent_layers_implementation_plan.md"
depends_on_phase_ids: ["6"]
execution_mode: "deterministic"
---

# Phase 7 - Observability Layer Agent Guide

## Goal

Make agent behavior inspectable and debuggable.

## Required Inputs

- Source plan: guides-codex/production_agent_layers_implementation_plan.md
- Phase dependencies marked complete in prior phase guides.
- Service/API codebase access and migration tooling access.
- Test environment with PostgreSQL and pgvector available.

## Build Checklist

- [ ] Add structured logs with request/agent/tenant IDs, memory access, tool calls, and policy decisions.
- [ ] Add metrics: request/tool/retrieval/embedding latency, token usage, cost estimate, error rates.
- [ ] Add tracing spans: agent request, retrieval, LLM call, tool call, DB.
- [ ] Build dashboards for activity, failures, memory writes, retrieval quality, and tool usage.
- [ ] Add alerts for error rate spikes, DB latency, embedding failures, unauthorized access, tool timeouts.

## Required Deliverables

- [ ] Logging schema.
- [ ] Metrics dashboard.
- [ ] Distributed traces.
- [ ] Alert rules.

## Verification Gates

- [ ] A failed agent task is traceable end to end from request to tool execution.
- [ ] Automated tests or scripted checks exist for all new critical paths.
- [ ] Evidence artifacts are produced under guides-codex/phases/evidence/phase-07/.

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

1. "Implement exactly Phase 7 (Observability Layer) from guides-codex/production_agent_layers_implementation_plan.md."
2. "Follow the checklist and deliverables in this file; do not skip verification gates."
3. "Write evidence artifacts under guides-codex/phases/evidence/phase-07/."
4. "Return: summary, changed files, test commands run, and gate status."
