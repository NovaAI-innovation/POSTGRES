---
phase_id: "12"
phase_key: "human-control-layer"
phase_name: "Human Control Layer"
source_plan: "guides-codex/production_agent_layers_implementation_plan.md"
depends_on_phase_ids: ["11"]
execution_mode: "deterministic"
---

# Phase 12 - Human Control Layer Agent Guide

## Goal

Give operators visibility and control over agents and memory.

## Required Inputs

- Source plan: guides-codex/production_agent_layers_implementation_plan.md
- Phase dependencies marked complete in prior phase guides.
- Service/API codebase access and migration tooling access.
- Test environment with PostgreSQL and pgvector available.

## Build Checklist

- [ ] Build admin UI pages: agents, groups, permissions, memory search/detail, tool calls, tasks, approvals, audit events.
- [ ] Add admin actions: disable agent, set read-only, delete/restore memory, adjust scores, approve/reject tools, inspect prompt context.
- [ ] Add audit trail for all admin actions.
- [ ] Add role-based admin access.
- [ ] Add emergency controls: pause agents, disable tool class, revoke credentials, block shared-memory writes.

## Required Deliverables

- [ ] Operator/admin console.
- [ ] Approval queue.
- [ ] Emergency stop controls.
- [ ] Audit event viewer.

## Verification Gates

- [ ] Operators can inspect, correct, disable, or roll back behavior without direct DB access.
- [ ] Automated tests or scripted checks exist for all new critical paths.
- [ ] Evidence artifacts are produced under guides-codex/phases/evidence/phase-12/.

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

1. "Implement exactly Phase 12 (Human Control Layer) from guides-codex/production_agent_layers_implementation_plan.md."
2. "Follow the checklist and deliverables in this file; do not skip verification gates."
3. "Write evidence artifacts under guides-codex/phases/evidence/phase-12/."
4. "Return: summary, changed files, test commands run, and gate status."
