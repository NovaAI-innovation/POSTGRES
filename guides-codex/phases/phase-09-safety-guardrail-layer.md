---
phase_id: "9"
phase_key: "safety-guardrail-layer"
phase_name: "Safety and Guardrail Layer"
source_plan: "guides-codex/production_agent_layers_implementation_plan.md"
depends_on_phase_ids: ["8"]
execution_mode: "deterministic"
---

# Phase 9 - Safety and Guardrail Layer Agent Guide

## Goal

Reduce unsafe actions, data leakage, and prompt-injection risk.

## Required Inputs

- Source plan: guides-codex/production_agent_layers_implementation_plan.md
- Phase dependencies marked complete in prior phase guides.
- Service/API codebase access and migration tooling access.
- Test environment with PostgreSQL and pgvector available.

## Build Checklist

- [ ] Add input scanning for injection markers, secrets, PII, and malicious tool instructions.
- [ ] Add output validation for schema correctness, blocked content, and sensitive leakage.
- [ ] Quarantine untrusted tool/web/doc outputs and strip embedded instructions.
- [ ] Add memory write guardrails: avoid storing secrets by default, mark sensitive memory, require stronger permission for shared writes.
- [ ] Add retention rules: sensitive expiry and redaction-on-request.
- [ ] Add escalation paths: human approval, block response, safe fallback.

## Required Deliverables

- [ ] Guardrail middleware.
- [ ] Injection detector.
- [ ] PII/secrets detector.
- [ ] Memory redaction flow.
- [ ] Quarantine rules for untrusted content.

## Verification Gates

- [ ] Tool output cannot override system/developer policy.
- [ ] Secrets/sensitive data are not written to shared memory by default.
- [ ] Automated tests or scripted checks exist for all new critical paths.
- [ ] Evidence artifacts are produced under guides-codex/phases/evidence/phase-09/.

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

1. "Implement exactly Phase 9 (Safety and Guardrail Layer) from guides-codex/production_agent_layers_implementation_plan.md."
2. "Follow the checklist and deliverables in this file; do not skip verification gates."
3. "Write evidence artifacts under guides-codex/phases/evidence/phase-09/."
4. "Return: summary, changed files, test commands run, and gate status."
