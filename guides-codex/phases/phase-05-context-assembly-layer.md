---
phase_id: "5"
phase_key: "context-assembly-layer"
phase_name: "Context Assembly Layer"
source_plan: "guides-codex/production_agent_layers_implementation_plan.md"
depends_on_phase_ids: ["4"]
execution_mode: "deterministic"
---

# Phase 5 - Context Assembly Layer Agent Guide

## Goal

Convert retrieved memory into prompt-ready context without exceeding token budgets.

## Required Inputs

- Source plan: guides-codex/production_agent_layers_implementation_plan.md
- Phase dependencies marked complete in prior phase guides.
- Service/API codebase access and migration tooling access.
- Test environment with PostgreSQL and pgvector available.

## Build Checklist

- [ ] Implement token budgets for memory, tool results, and conversation history.
- [ ] Group context into preferences, project facts, recent events, task memories, warnings/constraints.
- [ ] Compress redundant memories while preserving source refs and uncertainty.
- [ ] Resolve conflicts: newest valid fact wins by default; higher confidence wins on tie; surface unresolved conflicts.
- [ ] Emit final context format: concise bullets, source IDs, scope labels, confidence when relevant.

## Required Deliverables

- [ ] Context assembler.
- [ ] Prompt memory block format.
- [ ] Conflict-resolution logic.
- [ ] Token-budget tests.

## Verification Gates

- [ ] Context fits configured token limits.
- [ ] Context includes source labels and does not silently hide conflicts.
- [ ] Automated tests or scripted checks exist for all new critical paths.
- [ ] Evidence artifacts are produced under guides-codex/phases/evidence/phase-05/.

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

1. "Implement exactly Phase 5 (Context Assembly Layer) from guides-codex/production_agent_layers_implementation_plan.md."
2. "Follow the checklist and deliverables in this file; do not skip verification gates."
3. "Write evidence artifacts under guides-codex/phases/evidence/phase-05/."
4. "Return: summary, changed files, test commands run, and gate status."
