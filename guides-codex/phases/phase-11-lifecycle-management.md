---
phase_id: "11"
phase_key: "lifecycle-management"
phase_name: "Lifecycle Management"
source_plan: "guides-codex/production_agent_layers_implementation_plan.md"
depends_on_phase_ids: ["10"]
execution_mode: "deterministic"
---

# Phase 11 - Lifecycle Management Agent Guide

## Goal

Keep memory accurate, compact, and recoverable over time.

## Required Inputs

- Source plan: guides-codex/production_agent_layers_implementation_plan.md
- Phase dependencies marked complete in prior phase guides.
- Service/API codebase access and migration tooling access.
- Test environment with PostgreSQL and pgvector available.

## Build Checklist

- [ ] Add memory decay with reinforcement and pinned/core fact exemptions.
- [ ] Detect stale facts from expiry, contradictions, and old source refs.
- [ ] Compact memory by summarizing old messages into episodes and archiving raw logs.
- [ ] Add backup and restore: daily backups, point-in-time recovery, restore drills.
- [ ] Add migration policy: forward-only, rollback strategy, migration tests.
- [ ] Add retention: per-tenant policy, sensitive expiry, soft-delete cleanup schedule.

## Required Deliverables

- [ ] Memory maintenance jobs.
- [ ] Backup/restore process.
- [ ] Retention policy.
- [ ] Migration runbook.

## Verification Gates

- [ ] Old memory does not degrade retrieval quality.
- [ ] Database restore from backup is verified.
- [ ] Automated tests or scripted checks exist for all new critical paths.
- [ ] Evidence artifacts are produced under guides-codex/phases/evidence/phase-11/.

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

1. "Implement exactly Phase 11 (Lifecycle Management) from guides-codex/production_agent_layers_implementation_plan.md."
2. "Follow the checklist and deliverables in this file; do not skip verification gates."
3. "Write evidence artifacts under guides-codex/phases/evidence/phase-11/."
4. "Return: summary, changed files, test commands run, and gate status."
