---
phase_id: "8"
phase_key: "evaluation-layer"
phase_name: "Evaluation Layer"
source_plan: "guides-codex/production_agent_layers_implementation_plan.md"
depends_on_phase_ids: ["7"]
execution_mode: "deterministic"
---

# Phase 8 - Evaluation Layer Agent Guide

## Goal

Prevent prompt, memory, and tool regressions.

## Required Inputs

- Source plan: guides-codex/production_agent_layers_implementation_plan.md
- Phase dependencies marked complete in prior phase guides.
- Service/API codebase access and migration tooling access.
- Test environment with PostgreSQL and pgvector available.

## Build Checklist

- [ ] Create eval datasets: recall, permission boundaries, tool use, refusal/safety, multi-agent handoff.
- [ ] Add automated scoring: success, relevance, hallucination, unauthorized access, tool correctness.
- [ ] Add regression suite triggered by prompt/retrieval/model/schema changes.
- [ ] Add golden traces for critical workflows.
- [ ] Add human review queue for low-confidence outputs.

## Required Deliverables

- [ ] Eval harness.
- [ ] Test datasets.
- [ ] Regression dashboard.
- [ ] Release gate thresholds.

## Verification Gates

- [ ] Prompt/model/retrieval changes cannot ship without passing core evals.
- [ ] Automated tests or scripted checks exist for all new critical paths.
- [ ] Evidence artifacts are produced under guides-codex/phases/evidence/phase-08/.

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

1. "Implement exactly Phase 8 (Evaluation Layer) from guides-codex/production_agent_layers_implementation_plan.md."
2. "Follow the checklist and deliverables in this file; do not skip verification gates."
3. "Write evidence artifacts under guides-codex/phases/evidence/phase-08/."
4. "Return: summary, changed files, test commands run, and gate status."
