---
phase_id: "10"
phase_key: "orchestration-layer"
phase_name: "Orchestration Layer"
source_plan: "guides-codex/production_agent_layers_implementation_plan.md"
depends_on_phase_ids: ["9"]
execution_mode: "deterministic"
---

# Phase 10 - Orchestration Layer Agent Guide

## Goal

Coordinate multi-agent work reliably.

## Required Inputs

- Source plan: guides-codex/production_agent_layers_implementation_plan.md
- Phase dependencies marked complete in prior phase guides.
- Service/API codebase access and migration tooling access.
- Test environment with PostgreSQL and pgvector available.

## Build Checklist

- [ ] Add task model with identity, status, priority, deadline, parent-child links.
- [ ] Add task queue states: pending, running, waiting_approval, failed, completed.
- [ ] Add routing by capability, tool access, memory group, and load.
- [ ] Add reliability controls: retries, idempotency keys, cancellation, timeouts, dead-letter queue.
- [ ] Add handoff protocol with source/target, summary, relevant memory IDs, requested output.
- [ ] Add locking to prevent duplicate execution and protect shared resources.

## Required Deliverables

- [ ] Task queue.
- [ ] Agent router.
- [ ] Handoff protocol.
- [ ] Retry/dead-letter handling.
- [ ] Idempotency layer.

## Verification Gates

- [ ] Multi-step tasks survive worker restarts and do not duplicate destructive actions.
- [ ] Automated tests or scripted checks exist for all new critical paths.
- [ ] Evidence artifacts are produced under guides-codex/phases/evidence/phase-10/.

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

1. "Implement exactly Phase 10 (Orchestration Layer) from guides-codex/production_agent_layers_implementation_plan.md."
2. "Follow the checklist and deliverables in this file; do not skip verification gates."
3. "Write evidence artifacts under guides-codex/phases/evidence/phase-10/."
4. "Return: summary, changed files, test commands run, and gate status."
