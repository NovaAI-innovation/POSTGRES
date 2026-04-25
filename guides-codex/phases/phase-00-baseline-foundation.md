---
phase_id: "0"
phase_key: "baseline-foundation"
phase_name: "Baseline Foundation"
source_plan: "guides-codex/production_agent_layers_implementation_plan.md"
depends_on_phase_ids: []
execution_mode: "deterministic"
---

# Phase 0 - Baseline Foundation Agent Guide

## Goal

Get the memory schema running behind a minimal service boundary.

## Required Inputs

- Source plan: guides-codex/production_agent_layers_implementation_plan.md
- Phase dependencies marked complete in prior phase guides.
- Service/API codebase access and migration tooling access.
- Test environment with PostgreSQL and pgvector available.

## Build Checklist

- [ ] Apply the bootstrap SQL migration.
- [ ] Create backend modules: agents, groups, memory, permissions, embeddings, tools, observability.
- [ ] Expose only service APIs to agents.
- [ ] Disable direct agent database access.
- [ ] Add env config: database URL, embedding model, auth keys, log level, tool timeouts.

## Required Deliverables

- [ ] Running PostgreSQL memory database.
- [ ] Backend service connected to DB.
- [ ] Health check endpoint.
- [ ] Migration command.
- [ ] Basic create/read memory endpoint.

## Verification Gates

- [ ] A test agent can create and retrieve isolated memory through the API.
- [ ] No agent has direct DB credentials.
- [ ] Automated tests or scripted checks exist for all new critical paths.
- [ ] Evidence artifacts are produced under guides-codex/phases/evidence/phase-00/.

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

1. "Implement exactly Phase 0 (Baseline Foundation) from guides-codex/production_agent_layers_implementation_plan.md."
2. "Follow the checklist and deliverables in this file; do not skip verification gates."
3. "Write evidence artifacts under guides-codex/phases/evidence/phase-00/."
4. "Return: summary, changed files, test commands run, and gate status."
