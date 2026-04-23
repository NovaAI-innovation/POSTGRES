---
name: agent-state-management
description: Manage multi-agent coordination, leases, and shared state via PostgreSQL for collision-free collaboration.
version: 1.0.0
---

# Agent Skill: Multi-Agent State Management

Use this skill whenever you are acting as an agent within the "Shared Agent State" ecosystem. This skill ensures that your actions are deterministic, auditable, and collision-free.

## 🧠 Core Philosophy: "State-First"
Agents never "infer" truth from chat history alone. They treat the PostgreSQL database as the single source of truth for project objectives, task status, and shared memory.

## 🛠 Available Tools
You have two sets of identical automation scripts depending on your environment:
- **Bash:** `agent-state.sh`, `reconcile.sh`
- **PowerShell:** `agent-state.ps1`, `reconcile.ps1`

## 🔄 The Standard Protocol (Phase 5)

Follow this loop for every major task:

### 1. Synchronize (Pull)
Before thinking or planning, synchronize your local state with the project state.
- **Action:** Run `./agent-state.sh pull` and `./agent-state.sh tasks`.
- **Goal:** Understand the current objective and find your next task.

### 2. Claim Authority (Lease)
If you are modifying a scoped resource (a task, a file, or a branch), you MUST claim a lease.
- **Action:** `./agent-state.sh lease-claim [scope] [key] [agent_key] [reason]`
- **Rule:** If the lease claim fails, someone else is working on it. Do not proceed.

### 3. Execution & Event Logging
For every milestone achieved during work, append an event.
- **Action:** `./agent-state.sh event [agent_key] [type] [scope] [scope_key] [idemp_key] [payload]`
- **Rule:** Use a unique `idemp_key` (e.g., `fix-bug-123456`) to ensure that if you retry the command, it doesn't duplicate.

### 4. Materialize State
After an event, update the "Current State" table so other agents can see the result without reading the entire event log.
- **Action:** `./agent-state.sh state [agent_key] [scope] [scope_key] [state_key] [value_json] [event_id]`

### 5. Handoff & Release
When your part is done, create a handoff if another agent needs to review or continue.
- **Action:** `./agent-state.sh handoff [from] [to] [subject] [payload]`
- **Action:** `./agent-state.sh lease-release [scope] [key] [agent_key] [token]`

## 🧹 Maintenance (Phase 6)
If you notice stale locks or old tasks that were never closed, run the reconciliation script.
- **Action:** `./reconcile.sh`

## ⚠️ Security & Constraints
- Always ensure `.env` is present in the working directory.
- Never write directly to `core` or `shared` tables; always use the `api.*` functions via these scripts or the `agent-state` utility.
- Keep payloads as valid JSON.
