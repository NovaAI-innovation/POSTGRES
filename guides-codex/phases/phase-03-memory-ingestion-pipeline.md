---
phase_id: "3"
phase_key: "memory-ingestion-pipeline"
phase_name: "Memory Ingestion Pipeline"
source_plan: "guides-codex/production_agent_layers_implementation_plan.md"
depends_on_phase_ids: ["2"]
execution_mode: "deterministic"
---

# Phase 3 - Memory Ingestion Pipeline Agent Guide

## Goal

Turn raw agent/user/tool events into clean, searchable memory.

## Required Inputs

- Source plan: guides-codex/production_agent_layers_implementation_plan.md
- Phase dependencies marked complete in prior phase guides.
- Service/API codebase access and migration tooling access.
- Test environment with PostgreSQL and pgvector available.

## Build Checklist

- [ ] Create ingestion endpoint/job for raw events with metadata, owner agent, and scope.
- [ ] Normalize content: trim noise, remove duplicate boilerplate, preserve source ref.
- [ ] Classify entries: fact, episode, message.
- [ ] Extract facts, outcomes, preferences, and durable constraints.
- [ ] Score importance (0-100), confidence (0.00-1.00), and validity windows.
- [ ] Generate embeddings with 384 dimensions and normalize if cosine search is used.
- [ ] Tag entries by project/user/domain/task type.
- [ ] Deduplicate by content hash, near-duplicate vector threshold, and source-ref uniqueness.

## Required Deliverables

- [ ] Ingestion worker.
- [ ] Embedding generator.
- [ ] Memory classifier.
- [ ] Importance/confidence scorer.
- [ ] Deduplication logic.

## Verification Gates

- [ ] Raw messages convert into structured memory entries.
- [ ] Duplicate memories are not repeatedly inserted.
- [ ] Embedding dimension is validated before insert.
- [ ] Automated tests or scripted checks exist for all new critical paths.
- [ ] Evidence artifacts are produced under guides-codex/phases/evidence/phase-03/.

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

1. "Implement exactly Phase 3 (Memory Ingestion Pipeline) from guides-codex/production_agent_layers_implementation_plan.md."
2. "Follow the checklist and deliverables in this file; do not skip verification gates."
3. "Write evidence artifacts under guides-codex/phases/evidence/phase-03/."
4. "Return: summary, changed files, test commands run, and gate status."
