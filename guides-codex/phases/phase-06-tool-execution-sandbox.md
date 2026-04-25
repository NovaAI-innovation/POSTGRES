---
phase_id: "6"
phase_key: "tool-execution-sandbox"
phase_name: "Tool Execution Sandbox"
source_plan: "guides-codex/production_agent_layers_implementation_plan.md"
depends_on_phase_ids: ["5"]
execution_mode: "deterministic"
---

# Phase 6 - Tool Execution Sandbox Agent Guide

## Goal

Allow agents to use tools without uncontrolled side effects.

## Required Inputs

- Source plan: guides-codex/production_agent_layers_implementation_plan.md
- Phase dependencies marked complete in prior phase guides.
- Service/API codebase access and migration tooling access.
- Test environment with PostgreSQL and pgvector available.

## Build Checklist

- [ ] Create tool registry with schemas, permissions, timeout, rate limit, and destructive flag.
- [ ] Add execution wrapper with input validation, timeout, retry policy, structured output, and error capture.
- [ ] Add approval gates for destructive actions, external sends, payments, deploys, and deletions.
- [ ] Add dry-run mode.
- [ ] Add per-agent tool allowlists.
- [ ] Log each tool call with hashes, duration, status, and approval data.

## Required Deliverables

- [ ] Tool registry.
- [ ] Tool runner.
- [ ] Approval flow.
- [ ] Dry-run support.
- [ ] Tool audit logs.

## Verification Gates

- [ ] Agents cannot call unapproved tools.
- [ ] Destructive tools require explicit approval or elevated policy.
- [ ] Automated tests or scripted checks exist for all new critical paths.
- [ ] Evidence artifacts are produced under guides-codex/phases/evidence/phase-06/.

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

1. "Implement exactly Phase 6 (Tool Execution Sandbox) from guides-codex/production_agent_layers_implementation_plan.md."
2. "Follow the checklist and deliverables in this file; do not skip verification gates."
3. "Write evidence artifacts under guides-codex/phases/evidence/phase-06/."
4. "Return: summary, changed files, test commands run, and gate status."
