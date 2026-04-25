---
phase_id: "4"
phase_key: "memory-retrieval-layer"
phase_name: "Memory Retrieval Layer"
source_plan: "guides-codex/production_agent_layers_implementation_plan.md"
depends_on_phase_ids: ["3"]
execution_mode: "deterministic"
---

# Phase 4 - Memory Retrieval Layer Agent Guide

## Goal

Retrieve the right memory, not just the nearest vector result.

## Required Inputs

- Source plan: guides-codex/production_agent_layers_implementation_plan.md
- Phase dependencies marked complete in prior phase guides.
- Service/API codebase access and migration tooling access.
- Test environment with PostgreSQL and pgvector available.

## Build Checklist

- [ ] Implement readable-memory retrieval using DB helper function.
- [ ] Add hybrid retrieval: vector similarity, keyword search, recency, importance, confidence, scope priority.
- [ ] Add filters: entry_type, tag, domain, source_ref, valid time window.
- [ ] Add reranking with semantic score plus boosts/decays for importance, recency, confidence, exact keyword match.
- [ ] Deduplicate after retrieval.
- [ ] Attach citation/source labels.
- [ ] Add retrieval debug mode.

## Required Deliverables

- [ ] retrieve_memory(agent_id, query, filters) service.
- [ ] Hybrid score formula.
- [ ] Retrieval tests.
- [ ] Debug payload for memory selection rationale.

## Verification Gates

- [ ] Retrieval respects isolated/scoped/shared permissions.
- [ ] Old low-confidence irrelevant memories do not dominate context.
- [ ] Automated tests or scripted checks exist for all new critical paths.
- [ ] Evidence artifacts are produced under guides-codex/phases/evidence/phase-04/.

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

1. "Implement exactly Phase 4 (Memory Retrieval Layer) from guides-codex/production_agent_layers_implementation_plan.md."
2. "Follow the checklist and deliverables in this file; do not skip verification gates."
3. "Write evidence artifacts under guides-codex/phases/evidence/phase-04/."
4. "Return: summary, changed files, test commands run, and gate status."
