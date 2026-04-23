## Multi-phase plan

### Phase 1 — Foundation

Create four schemas:

* `core`: projects, agents, memberships
* `shared`: append-only event log plus shared state
* `ext`: per-agent extension tables
* `api`: only-approved write functions

Use this model:

* **append-only events** = immutable audit/history
* **materialized current state tables** = fast reads
* **agent extension tables** = tool/runtime-specific persistence
* **idempotent API functions** = deterministic row population

### Phase 2 — Canonical shared model

Persist these categories:

* projects
* agent registry
* project-agent membership
* shared key/value state
* tasks
* decisions
* artifacts
* handoffs
* leases
* event log

### Phase 3 — Deterministic write layer

Every write goes through functions that:

* acquire a transaction advisory lock on the project
* normalize keys
* upsert by natural key
* bump row versions
* append an event row with an `idempotency_key`

### Phase 4 — Agent-specific extension state

Each agent gets its own table for runtime/tool specifics:

* workspace root
* cwd
* current branch
* last prompt digest
* active plan
* pending tool actions
* model/tool config
* local file summary
* compact memory

### Phase 5 — Read contracts

Agents never “infer” truth from chat alone. They always:

1. read project
2. read current tasks/decisions/shared state
3. read their own extension row
4. claim lease
5. do work
6. write event + shared updates + extension update + handoff if needed

### Phase 6 — Operations

Add:

* retention/archiving for old events
* per-project snapshots
* background reconciliation job
* optional RLS later if you split agents across trust zones

---

## Schema bootstrap SQL

```sql
BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS shared;
CREATE SCHEMA IF NOT EXISTS ext;
CREATE SCHEMA IF NOT EXISTS api;

-- ----------------------------
-- Utility functions
-- ----------------------------

CREATE OR REPLACE FUNCTION api.canonical_key(input text)
RETURNS text
LANGUAGE sql
IMMUTABLE
AS $$
  SELECT trim(both '-' from regexp_replace(lower(coalesce(input,'')), '[^a-z0-9]+', '-', 'g'));
$$;

CREATE OR REPLACE FUNCTION api.set_timestamps()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    NEW.created_at := COALESCE(NEW.created_at, now());
  END IF;
  NEW.updated_at := now();
  RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION api.bump_row_version()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    NEW.row_version := COALESCE(NEW.row_version, 1);
  ELSE
    NEW.row_version := OLD.row_version + 1;
  END IF;
  RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION api.project_lock_key(p_project_id bigint)
RETURNS bigint
LANGUAGE sql
IMMUTABLE
AS $$
  SELECT COALESCE(p_project_id, 0)::bigint;
$$;

-- ----------------------------
-- Core tables
-- ----------------------------

CREATE TABLE IF NOT EXISTS core.projects (
  project_id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  external_key        text NOT NULL UNIQUE,
  project_name        text NOT NULL,
  project_slug        text GENERATED ALWAYS AS (api.canonical_key(project_name)) STORED,
  status              text NOT NULL DEFAULT 'active'
                      CHECK (status IN ('active','paused','archived','completed')),
  default_branch      text,
  repo_url            text,
  metadata            jsonb NOT NULL DEFAULT '{}'::jsonb,
  row_version         bigint NOT NULL DEFAULT 1,
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS core.agents (
  agent_id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  agent_key           text NOT NULL UNIQUE,   -- claude-code, gemini-cli, openai-codex, etc.
  agent_family        text NOT NULL,          -- cli, coder, orchestrator, reviewer, etc.
  display_name        text NOT NULL,
  model_hint          text,
  capabilities        jsonb NOT NULL DEFAULT '[]'::jsonb,
  config              jsonb NOT NULL DEFAULT '{}'::jsonb,
  is_active           boolean NOT NULL DEFAULT true,
  row_version         bigint NOT NULL DEFAULT 1,
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS core.project_agents (
  project_id          bigint NOT NULL REFERENCES core.projects(project_id) ON DELETE CASCADE,
  agent_id            bigint NOT NULL REFERENCES core.agents(agent_id) ON DELETE CASCADE,
  role_name           text NOT NULL DEFAULT 'worker',
  can_write_shared    boolean NOT NULL DEFAULT true,
  priority_weight     integer NOT NULL DEFAULT 100,
  membership_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  row_version         bigint NOT NULL DEFAULT 1,
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (project_id, agent_id)
);

-- ----------------------------
-- Shared event log
-- ----------------------------

CREATE TABLE IF NOT EXISTS shared.events (
  event_id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  project_id          bigint NOT NULL REFERENCES core.projects(project_id) ON DELETE CASCADE,
  agent_id            bigint REFERENCES core.agents(agent_id) ON DELETE SET NULL,
  event_type          text NOT NULL,  -- task.updated, decision.made, artifact.added, lease.claimed...
  scope_type          text NOT NULL,  -- project/task/artifact/branch/file/agent/global
  scope_key           text NOT NULL DEFAULT '',
  idempotency_key     text NOT NULL,
  event_payload       jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at          timestamptz NOT NULL DEFAULT now(),
  UNIQUE (project_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_events_project_created
  ON shared.events(project_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_events_payload_gin
  ON shared.events USING gin (event_payload jsonb_path_ops);

-- ----------------------------
-- Shared current state
-- ----------------------------

CREATE TABLE IF NOT EXISTS shared.core_state (
  state_id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  project_id          bigint REFERENCES core.projects(project_id) ON DELETE CASCADE,
  scope_type          text NOT NULL,   -- global/project/task/file/branch/agent/artifact
  scope_key           text NOT NULL DEFAULT '',
  state_key           text NOT NULL,   -- objective, repo.branch, build.status, api.contract
  value_json          jsonb NOT NULL DEFAULT '{}'::jsonb,
  value_text          text,
  source_event_id     bigint REFERENCES shared.events(event_id) ON DELETE SET NULL,
  source_agent_id     bigint REFERENCES core.agents(agent_id) ON DELETE SET NULL,
  confidence          numeric(5,4),
  effective_at        timestamptz NOT NULL DEFAULT now(),
  expires_at          timestamptz,
  row_version         bigint NOT NULL DEFAULT 1,
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now(),
  UNIQUE (project_id, scope_type, scope_key, state_key)
);

CREATE INDEX IF NOT EXISTS idx_core_state_lookup
  ON shared.core_state(project_id, scope_type, scope_key, state_key);

CREATE INDEX IF NOT EXISTS idx_core_state_json_gin
  ON shared.core_state USING gin (value_json jsonb_path_ops);

-- ----------------------------
-- Tasks
-- ----------------------------

CREATE TABLE IF NOT EXISTS shared.tasks (
  task_id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  project_id          bigint NOT NULL REFERENCES core.projects(project_id) ON DELETE CASCADE,
  parent_task_id      bigint REFERENCES shared.tasks(task_id) ON DELETE SET NULL,
  canonical_title     text NOT NULL,
  title               text NOT NULL,
  description         text,
  status              text NOT NULL DEFAULT 'todo'
                      CHECK (status IN ('todo','in_progress','blocked','review','done','cancelled')),
  priority            text NOT NULL DEFAULT 'medium'
                      CHECK (priority IN ('low','medium','high','critical')),
  assigned_agent_id   bigint REFERENCES core.agents(agent_id) ON DELETE SET NULL,
  requested_by_agent_id bigint REFERENCES core.agents(agent_id) ON DELETE SET NULL,
  depends_on          jsonb NOT NULL DEFAULT '[]'::jsonb,
  acceptance_criteria jsonb NOT NULL DEFAULT '[]'::jsonb,
  task_metadata       jsonb NOT NULL DEFAULT '{}'::jsonb,
  row_version         bigint NOT NULL DEFAULT 1,
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now(),
  UNIQUE (project_id, canonical_title)
);

CREATE INDEX IF NOT EXISTS idx_tasks_project_status
  ON shared.tasks(project_id, status, priority, updated_at DESC);

-- ----------------------------
-- Decisions
-- ----------------------------

CREATE TABLE IF NOT EXISTS shared.decisions (
  decision_id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  project_id          bigint NOT NULL REFERENCES core.projects(project_id) ON DELETE CASCADE,
  decision_key        text NOT NULL,
  title               text NOT NULL,
  summary             text NOT NULL,
  rationale           text,
  chosen_option       jsonb NOT NULL DEFAULT '{}'::jsonb,
  alternatives        jsonb NOT NULL DEFAULT '[]'::jsonb,
  supersedes_decision_id bigint REFERENCES shared.decisions(decision_id) ON DELETE SET NULL,
  made_by_agent_id    bigint REFERENCES core.agents(agent_id) ON DELETE SET NULL,
  row_version         bigint NOT NULL DEFAULT 1,
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now(),
  UNIQUE (project_id, decision_key)
);

-- ----------------------------
-- Artifacts
-- ----------------------------

CREATE TABLE IF NOT EXISTS shared.artifacts (
  artifact_id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  project_id          bigint NOT NULL REFERENCES core.projects(project_id) ON DELETE CASCADE,
  artifact_type       text NOT NULL,      -- file, doc, schema, prompt, api, migration, build
  artifact_key        text NOT NULL,      -- e.g. repo:path or logical key
  location_uri        text,
  content_hash        text,
  version_label       text,
  producer_agent_id   bigint REFERENCES core.agents(agent_id) ON DELETE SET NULL,
  artifact_metadata   jsonb NOT NULL DEFAULT '{}'::jsonb,
  row_version         bigint NOT NULL DEFAULT 1,
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now(),
  UNIQUE (project_id, artifact_type, artifact_key, COALESCE(version_label, 'current'))
);

CREATE INDEX IF NOT EXISTS idx_artifacts_project_type
  ON shared.artifacts(project_id, artifact_type, updated_at DESC);

-- ----------------------------
-- Handoffs
-- ----------------------------

CREATE TABLE IF NOT EXISTS shared.handoffs (
  handoff_id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  project_id          bigint NOT NULL REFERENCES core.projects(project_id) ON DELETE CASCADE,
  from_agent_id       bigint REFERENCES core.agents(agent_id) ON DELETE SET NULL,
  to_agent_id         bigint REFERENCES core.agents(agent_id) ON DELETE SET NULL,
  handoff_kind        text NOT NULL DEFAULT 'work',
  status              text NOT NULL DEFAULT 'open'
                      CHECK (status IN ('open','accepted','rejected','completed')),
  subject             text NOT NULL,
  payload             jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now()
);

-- ----------------------------
-- Leases / coordination
-- ----------------------------

CREATE TABLE IF NOT EXISTS shared.agent_leases (
  lease_id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  project_id          bigint NOT NULL REFERENCES core.projects(project_id) ON DELETE CASCADE,
  agent_id            bigint NOT NULL REFERENCES core.agents(agent_id) ON DELETE CASCADE,
  lease_scope_type    text NOT NULL,   -- project/task/file/branch
  lease_scope_key     text NOT NULL DEFAULT '',
  lease_reason        text NOT NULL,
  lease_token         uuid NOT NULL DEFAULT gen_random_uuid(),
  acquired_at         timestamptz NOT NULL DEFAULT now(),
  expires_at          timestamptz NOT NULL,
  released_at         timestamptz,
  UNIQUE (project_id, lease_scope_type, lease_scope_key, released_at)
);

CREATE INDEX IF NOT EXISTS idx_leases_active
  ON shared.agent_leases(project_id, lease_scope_type, lease_scope_key, expires_at)
  WHERE released_at IS NULL;

-- ----------------------------
-- Agent runtime base pattern
-- ----------------------------

CREATE TABLE IF NOT EXISTS ext.agent_runtime_base (
  project_id          bigint NOT NULL REFERENCES core.projects(project_id) ON DELETE CASCADE,
  agent_id            bigint NOT NULL REFERENCES core.agents(agent_id) ON DELETE CASCADE,
  workspace_root      text,
  cwd                 text,
  active_branch       text,
  active_task_key     text,
  local_state         jsonb NOT NULL DEFAULT '{}'::jsonb,
  compact_memory      jsonb NOT NULL DEFAULT '{}'::jsonb,
  pending_actions     jsonb NOT NULL DEFAULT '[]'::jsonb,
  last_prompt_digest  text,
  last_seen_event_id  bigint REFERENCES shared.events(event_id) ON DELETE SET NULL,
  row_version         bigint NOT NULL DEFAULT 1,
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (project_id, agent_id)
);

CREATE TABLE IF NOT EXISTS ext.claude_code_state (
  like ext.agent_runtime_base INCLUDING ALL,
  session_transcript_ref text,
  patch_queue           jsonb NOT NULL DEFAULT '[]'::jsonb
);

CREATE TABLE IF NOT EXISTS ext.gemini_cli_state (
  like ext.agent_runtime_base INCLUDING ALL,
  notebook_context      jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS ext.openai_codex_state (
  like ext.agent_runtime_base INCLUDING ALL,
  code_review_queue     jsonb NOT NULL DEFAULT '[]'::jsonb
);

CREATE TABLE IF NOT EXISTS ext.agent_zero_state (
  like ext.agent_runtime_base INCLUDING ALL,
  planner_state         jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS ext.openclaw_state (
  like ext.agent_runtime_base INCLUDING ALL,
  toolchain_state       jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS ext.hermes_state (
  like ext.agent_runtime_base INCLUDING ALL,
  memory_threads        jsonb NOT NULL DEFAULT '[]'::jsonb
);

-- ----------------------------
-- Triggers
-- ----------------------------

CREATE TRIGGER trg_projects_ts
BEFORE INSERT OR UPDATE ON core.projects
FOR EACH ROW EXECUTE FUNCTION api.set_timestamps();

CREATE TRIGGER trg_agents_ts
BEFORE INSERT OR UPDATE ON core.agents
FOR EACH ROW EXECUTE FUNCTION api.set_timestamps();

CREATE TRIGGER trg_project_agents_ts
BEFORE INSERT OR UPDATE ON core.project_agents
FOR EACH ROW EXECUTE FUNCTION api.set_timestamps();

CREATE TRIGGER trg_core_state_ts
BEFORE INSERT OR UPDATE ON shared.core_state
FOR EACH ROW EXECUTE FUNCTION api.set_timestamps();

CREATE TRIGGER trg_tasks_ts
BEFORE INSERT OR UPDATE ON shared.tasks
FOR EACH ROW EXECUTE FUNCTION api.set_timestamps();

CREATE TRIGGER trg_decisions_ts
BEFORE INSERT OR UPDATE ON shared.decisions
FOR EACH ROW EXECUTE FUNCTION api.set_timestamps();

CREATE TRIGGER trg_artifacts_ts
BEFORE INSERT OR UPDATE ON shared.artifacts
FOR EACH ROW EXECUTE FUNCTION api.set_timestamps();

CREATE TRIGGER trg_handoffs_ts
BEFORE INSERT OR UPDATE ON shared.handoffs
FOR EACH ROW EXECUTE FUNCTION api.set_timestamps();

CREATE TRIGGER trg_projects_ver
BEFORE UPDATE ON core.projects
FOR EACH ROW EXECUTE FUNCTION api.bump_row_version();

CREATE TRIGGER trg_agents_ver
BEFORE UPDATE ON core.agents
FOR EACH ROW EXECUTE FUNCTION api.bump_row_version();

CREATE TRIGGER trg_project_agents_ver
BEFORE UPDATE ON core.project_agents
FOR EACH ROW EXECUTE FUNCTION api.bump_row_version();

CREATE TRIGGER trg_core_state_ver
BEFORE UPDATE ON shared.core_state
FOR EACH ROW EXECUTE FUNCTION api.bump_row_version();

CREATE TRIGGER trg_tasks_ver
BEFORE UPDATE ON shared.tasks
FOR EACH ROW EXECUTE FUNCTION api.bump_row_version();

CREATE TRIGGER trg_decisions_ver
BEFORE UPDATE ON shared.decisions
FOR EACH ROW EXECUTE FUNCTION api.bump_row_version();

CREATE TRIGGER trg_artifacts_ver
BEFORE UPDATE ON shared.artifacts
FOR EACH ROW EXECUTE FUNCTION api.bump_row_version();

-- ----------------------------
-- Deterministic API functions
-- ----------------------------

CREATE OR REPLACE FUNCTION api.register_project(
  p_external_key text,
  p_project_name text,
  p_default_branch text DEFAULT NULL,
  p_repo_url text DEFAULT NULL,
  p_metadata jsonb DEFAULT '{}'::jsonb
) RETURNS bigint
LANGUAGE plpgsql
AS $$
DECLARE
  v_project_id bigint;
BEGIN
  INSERT INTO core.projects (external_key, project_name, default_branch, repo_url, metadata)
  VALUES (p_external_key, p_project_name, p_default_branch, p_repo_url, COALESCE(p_metadata, '{}'::jsonb))
  ON CONFLICT (external_key)
  DO UPDATE SET
    project_name = EXCLUDED.project_name,
    default_branch = EXCLUDED.default_branch,
    repo_url = EXCLUDED.repo_url,
    metadata = core.projects.metadata || EXCLUDED.metadata
  RETURNING project_id INTO v_project_id;

  RETURN v_project_id;
END;
$$;

CREATE OR REPLACE FUNCTION api.register_agent(
  p_agent_key text,
  p_agent_family text,
  p_display_name text,
  p_model_hint text DEFAULT NULL,
  p_capabilities jsonb DEFAULT '[]'::jsonb,
  p_config jsonb DEFAULT '{}'::jsonb
) RETURNS bigint
LANGUAGE plpgsql
AS $$
DECLARE
  v_agent_id bigint;
BEGIN
  INSERT INTO core.agents(agent_key, agent_family, display_name, model_hint, capabilities, config)
  VALUES (p_agent_key, p_agent_family, p_display_name, p_model_hint, COALESCE(p_capabilities,'[]'::jsonb), COALESCE(p_config,'{}'::jsonb))
  ON CONFLICT (agent_key)
  DO UPDATE SET
    agent_family = EXCLUDED.agent_family,
    display_name = EXCLUDED.display_name,
    model_hint = EXCLUDED.model_hint,
    capabilities = EXCLUDED.capabilities,
    config = core.agents.config || EXCLUDED.config,
    is_active = true
  RETURNING agent_id INTO v_agent_id;

  RETURN v_agent_id;
END;
$$;

CREATE OR REPLACE FUNCTION api.attach_agent_to_project(
  p_project_id bigint,
  p_agent_id bigint,
  p_role_name text DEFAULT 'worker',
  p_can_write_shared boolean DEFAULT true,
  p_priority_weight integer DEFAULT 100,
  p_membership_metadata jsonb DEFAULT '{}'::jsonb
) RETURNS void
LANGUAGE sql
AS $$
  INSERT INTO core.project_agents(project_id, agent_id, role_name, can_write_shared, priority_weight, membership_metadata)
  VALUES ($1, $2, $3, $4, $5, COALESCE($6, '{}'::jsonb))
  ON CONFLICT (project_id, agent_id)
  DO UPDATE SET
    role_name = EXCLUDED.role_name,
    can_write_shared = EXCLUDED.can_write_shared,
    priority_weight = EXCLUDED.priority_weight,
    membership_metadata = core.project_agents.membership_metadata || EXCLUDED.membership_metadata;
$$;

CREATE OR REPLACE FUNCTION api.append_event(
  p_project_id bigint,
  p_agent_id bigint,
  p_event_type text,
  p_scope_type text,
  p_scope_key text,
  p_idempotency_key text,
  p_event_payload jsonb DEFAULT '{}'::jsonb
) RETURNS bigint
LANGUAGE plpgsql
AS $$
DECLARE
  v_event_id bigint;
BEGIN
  PERFORM pg_advisory_xact_lock(api.project_lock_key(p_project_id));

  INSERT INTO shared.events(project_id, agent_id, event_type, scope_type, scope_key, idempotency_key, event_payload)
  VALUES (p_project_id, p_agent_id, p_event_type, p_scope_type, COALESCE(p_scope_key,''), p_idempotency_key, COALESCE(p_event_payload,'{}'::jsonb))
  ON CONFLICT (project_id, idempotency_key)
  DO UPDATE SET event_payload = shared.events.event_payload
  RETURNING event_id INTO v_event_id;

  RETURN v_event_id;
END;
$$;

CREATE OR REPLACE FUNCTION api.upsert_core_state(
  p_project_id bigint,
  p_agent_id bigint,
  p_scope_type text,
  p_scope_key text,
  p_state_key text,
  p_value_json jsonb DEFAULT '{}'::jsonb,
  p_value_text text DEFAULT NULL,
  p_source_event_id bigint DEFAULT NULL,
  p_confidence numeric DEFAULT NULL,
  p_effective_at timestamptz DEFAULT now(),
  p_expires_at timestamptz DEFAULT NULL
) RETURNS bigint
LANGUAGE plpgsql
AS $$
DECLARE
  v_state_id bigint;
BEGIN
  PERFORM pg_advisory_xact_lock(api.project_lock_key(p_project_id));

  INSERT INTO shared.core_state(
    project_id, scope_type, scope_key, state_key, value_json, value_text,
    source_event_id, source_agent_id, confidence, effective_at, expires_at
  )
  VALUES (
    p_project_id, p_scope_type, COALESCE(p_scope_key,''), p_state_key, COALESCE(p_value_json,'{}'::jsonb), p_value_text,
    p_source_event_id, p_agent_id, p_confidence, COALESCE(p_effective_at, now()), p_expires_at
  )
  ON CONFLICT (project_id, scope_type, scope_key, state_key)
  DO UPDATE SET
    value_json = EXCLUDED.value_json,
    value_text = EXCLUDED.value_text,
    source_event_id = EXCLUDED.source_event_id,
    source_agent_id = EXCLUDED.source_agent_id,
    confidence = EXCLUDED.confidence,
    effective_at = EXCLUDED.effective_at,
    expires_at = EXCLUDED.expires_at
  RETURNING state_id INTO v_state_id;

  RETURN v_state_id;
END;
$$;

CREATE OR REPLACE FUNCTION api.upsert_task(
  p_project_id bigint,
  p_title text,
  p_description text DEFAULT NULL,
  p_status text DEFAULT 'todo',
  p_priority text DEFAULT 'medium',
  p_assigned_agent_id bigint DEFAULT NULL,
  p_requested_by_agent_id bigint DEFAULT NULL,
  p_depends_on jsonb DEFAULT '[]'::jsonb,
  p_acceptance_criteria jsonb DEFAULT '[]'::jsonb,
  p_task_metadata jsonb DEFAULT '{}'::jsonb
) RETURNS bigint
LANGUAGE plpgsql
AS $$
DECLARE
  v_task_id bigint;
  v_canonical_title text;
BEGIN
  v_canonical_title := api.canonical_key(p_title);

  PERFORM pg_advisory_xact_lock(api.project_lock_key(p_project_id));

  INSERT INTO shared.tasks(
    project_id, canonical_title, title, description, status, priority,
    assigned_agent_id, requested_by_agent_id, depends_on, acceptance_criteria, task_metadata
  )
  VALUES (
    p_project_id, v_canonical_title, p_title, p_description, p_status, p_priority,
    p_assigned_agent_id, p_requested_by_agent_id, COALESCE(p_depends_on,'[]'::jsonb),
    COALESCE(p_acceptance_criteria,'[]'::jsonb), COALESCE(p_task_metadata,'{}'::jsonb)
  )
  ON CONFLICT (project_id, canonical_title)
  DO UPDATE SET
    description = COALESCE(EXCLUDED.description, shared.tasks.description),
    status = EXCLUDED.status,
    priority = EXCLUDED.priority,
    assigned_agent_id = EXCLUDED.assigned_agent_id,
    requested_by_agent_id = EXCLUDED.requested_by_agent_id,
    depends_on = EXCLUDED.depends_on,
    acceptance_criteria = EXCLUDED.acceptance_criteria,
    task_metadata = shared.tasks.task_metadata || EXCLUDED.task_metadata
  RETURNING task_id INTO v_task_id;

  RETURN v_task_id;
END;
$$;

CREATE OR REPLACE FUNCTION api.upsert_decision(
  p_project_id bigint,
  p_decision_key text,
  p_title text,
  p_summary text,
  p_rationale text DEFAULT NULL,
  p_chosen_option jsonb DEFAULT '{}'::jsonb,
  p_alternatives jsonb DEFAULT '[]'::jsonb,
  p_made_by_agent_id bigint DEFAULT NULL
) RETURNS bigint
LANGUAGE plpgsql
AS $$
DECLARE
  v_decision_id bigint;
BEGIN
  PERFORM pg_advisory_xact_lock(api.project_lock_key(p_project_id));

  INSERT INTO shared.decisions(
    project_id, decision_key, title, summary, rationale, chosen_option, alternatives, made_by_agent_id
  )
  VALUES (
    p_project_id, api.canonical_key(p_decision_key), p_title, p_summary, p_rationale,
    COALESCE(p_chosen_option,'{}'::jsonb), COALESCE(p_alternatives,'[]'::jsonb), p_made_by_agent_id
  )
  ON CONFLICT (project_id, decision_key)
  DO UPDATE SET
    title = EXCLUDED.title,
    summary = EXCLUDED.summary,
    rationale = EXCLUDED.rationale,
    chosen_option = EXCLUDED.chosen_option,
    alternatives = EXCLUDED.alternatives,
    made_by_agent_id = EXCLUDED.made_by_agent_id
  RETURNING decision_id INTO v_decision_id;

  RETURN v_decision_id;
END;
$$;

CREATE OR REPLACE FUNCTION api.upsert_artifact(
  p_project_id bigint,
  p_artifact_type text,
  p_artifact_key text,
  p_location_uri text DEFAULT NULL,
  p_content_hash text DEFAULT NULL,
  p_version_label text DEFAULT NULL,
  p_producer_agent_id bigint DEFAULT NULL,
  p_artifact_metadata jsonb DEFAULT '{}'::jsonb
) RETURNS bigint
LANGUAGE plpgsql
AS $$
DECLARE
  v_artifact_id bigint;
BEGIN
  PERFORM pg_advisory_xact_lock(api.project_lock_key(p_project_id));

  INSERT INTO shared.artifacts(
    project_id, artifact_type, artifact_key, location_uri, content_hash, version_label, producer_agent_id, artifact_metadata
  )
  VALUES (
    p_project_id, p_artifact_type, p_artifact_key, p_location_uri, p_content_hash, p_version_label, p_producer_agent_id,
    COALESCE(p_artifact_metadata,'{}'::jsonb)
  )
  ON CONFLICT (project_id, artifact_type, artifact_key, COALESCE(version_label, 'current'))
  DO UPDATE SET
    location_uri = EXCLUDED.location_uri,
    content_hash = EXCLUDED.content_hash,
    producer_agent_id = EXCLUDED.producer_agent_id,
    artifact_metadata = shared.artifacts.artifact_metadata || EXCLUDED.artifact_metadata
  RETURNING artifact_id INTO v_artifact_id;

  RETURN v_artifact_id;
END;
$$;

CREATE OR REPLACE FUNCTION api.claim_lease(
  p_project_id bigint,
  p_agent_id bigint,
  p_scope_type text,
  p_scope_key text,
  p_lease_reason text,
  p_ttl_seconds integer DEFAULT 900
) RETURNS uuid
LANGUAGE plpgsql
AS $$
DECLARE
  v_token uuid;
BEGIN
  PERFORM pg_advisory_xact_lock(api.project_lock_key(p_project_id));

  UPDATE shared.agent_leases
     SET released_at = now()
   WHERE project_id = p_project_id
     AND lease_scope_type = p_scope_type
     AND lease_scope_key = COALESCE(p_scope_key,'')
     AND released_at IS NULL
     AND expires_at <= now();

  IF EXISTS (
    SELECT 1
      FROM shared.agent_leases
     WHERE project_id = p_project_id
       AND lease_scope_type = p_scope_type
       AND lease_scope_key = COALESCE(p_scope_key,'')
       AND released_at IS NULL
       AND expires_at > now()
  ) THEN
    RAISE EXCEPTION 'active lease exists for %.%', p_scope_type, p_scope_key;
  END IF;

  INSERT INTO shared.agent_leases(
    project_id, agent_id, lease_scope_type, lease_scope_key, lease_reason, expires_at
  )
  VALUES (
    p_project_id, p_agent_id, p_scope_type, COALESCE(p_scope_key,''), p_lease_reason,
    now() + make_interval(secs => p_ttl_seconds)
  )
  RETURNING lease_token INTO v_token;

  RETURN v_token;
END;
$$;

CREATE OR REPLACE FUNCTION api.release_lease(
  p_project_id bigint,
  p_agent_id bigint,
  p_scope_type text,
  p_scope_key text,
  p_lease_token uuid
) RETURNS void
LANGUAGE sql
AS $$
  UPDATE shared.agent_leases
     SET released_at = now()
   WHERE project_id = $1
     AND agent_id = $2
     AND lease_scope_type = $3
     AND lease_scope_key = COALESCE($4,'')
     AND lease_token = $5
     AND released_at IS NULL;
$$;

CREATE OR REPLACE FUNCTION api.upsert_agent_runtime_state(
  p_agent_key text,
  p_project_id bigint,
  p_workspace_root text DEFAULT NULL,
  p_cwd text DEFAULT NULL,
  p_active_branch text DEFAULT NULL,
  p_active_task_key text DEFAULT NULL,
  p_local_state jsonb DEFAULT '{}'::jsonb,
  p_compact_memory jsonb DEFAULT '{}'::jsonb,
  p_pending_actions jsonb DEFAULT '[]'::jsonb,
  p_last_prompt_digest text DEFAULT NULL,
  p_last_seen_event_id bigint DEFAULT NULL
) RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
  v_agent_id bigint;
  v_table text;
BEGIN
  SELECT agent_id, replace(agent_key, '-', '_') || '_state'
    INTO v_agent_id, v_table
    FROM core.agents
   WHERE agent_key = p_agent_key;

  IF v_agent_id IS NULL THEN
    RAISE EXCEPTION 'unknown agent_key: %', p_agent_key;
  END IF;

  EXECUTE format(
    'INSERT INTO ext.%I
      (project_id, agent_id, workspace_root, cwd, active_branch, active_task_key,
       local_state, compact_memory, pending_actions, last_prompt_digest, last_seen_event_id)
     VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
     ON CONFLICT (project_id, agent_id)
     DO UPDATE SET
       workspace_root = EXCLUDED.workspace_root,
       cwd = EXCLUDED.cwd,
       active_branch = EXCLUDED.active_branch,
       active_task_key = EXCLUDED.active_task_key,
       local_state = EXCLUDED.local_state,
       compact_memory = EXCLUDED.compact_memory,
       pending_actions = EXCLUDED.pending_actions,
       last_prompt_digest = EXCLUDED.last_prompt_digest,
       last_seen_event_id = EXCLUDED.last_seen_event_id,
       updated_at = now()',
    v_table
  )
  USING p_project_id, v_agent_id, p_workspace_root, p_cwd, p_active_branch, p_active_task_key,
        COALESCE(p_local_state,'{}'::jsonb), COALESCE(p_compact_memory,'{}'::jsonb),
        COALESCE(p_pending_actions,'[]'::jsonb), p_last_prompt_digest, p_last_seen_event_id;
END;
$$;

COMMIT;
```

---

## Deterministic mechanisms for populating new rows

Use these rules everywhere:

1. **Projects**: `external_key` is the natural key. Always call `api.register_project`.
2. **Agents**: `agent_key` is the natural key. Always call `api.register_agent`.
3. **Tasks**: canonical title = `api.canonical_key(title)`. One logical task per project/title.
4. **Decisions**: `decision_key` is canonicalized and unique per project.
5. **Core state**: unique by `(project_id, scope_type, scope_key, state_key)`.
6. **Events**: unique by `(project_id, idempotency_key)`.
7. **Artifacts**: unique by `(project_id, artifact_type, artifact_key, version_label|null=current)`.
8. **Leases**: one active lease per scope.
9. **Agent runtime state**: one row per `(project_id, agent_id)` in that agent’s extension table.

Generated columns and identity columns are built-in mechanisms for deriving fields and generating keys, while advisory locks let you impose app-level coordination semantics around these deterministic upserts. ([PostgreSQL][2])

---

## Initial bootstrap queries

### 1) Register the project

```sql
SELECT api.register_project(
  'shared-agent-state',
  'Shared Agent State Layer',
  'main',
  'git@github.com:you/shared-agent-state.git',
  '{"language":"typescript","db":"postgres","purpose":"multi-agent shared awareness"}'::jsonb
) AS project_id;
```

### 2) Register agents

```sql
SELECT api.register_agent('claude-code', 'cli-coder', 'Claude Code', 'claude', '["coding","refactor","shell"]'::jsonb);
SELECT api.register_agent('gemini-cli', 'cli-coder', 'Gemini CLI', 'gemini', '["analysis","docs","shell"]'::jsonb);
SELECT api.register_agent('openai-codex', 'coder', 'OpenAI Codex', 'codex', '["coding","tests","review"]'::jsonb);
SELECT api.register_agent('agent-zero', 'orchestrator', 'Agent Zero', 'custom', '["planning","routing","coordination"]'::jsonb);
SELECT api.register_agent('openclaw', 'worker', 'OpenClaw', 'openclaw', '["coding","execution"]'::jsonb);
SELECT api.register_agent('hermes', 'memory', 'Hermes', 'hermes', '["memory","summaries","handoffs"]'::jsonb);
```

### 3) Attach agents to the project

```sql
WITH p AS (
  SELECT project_id FROM core.projects WHERE external_key = 'shared-agent-state'
)
INSERT INTO core.project_agents(project_id, agent_id, role_name)
SELECT p.project_id, a.agent_id,
       CASE a.agent_key
         WHEN 'agent-zero' THEN 'orchestrator'
         WHEN 'hermes' THEN 'memory'
         ELSE 'worker'
       END
FROM p
JOIN core.agents a ON a.agent_key IN (
  'claude-code','gemini-cli','openai-codex','agent-zero','openclaw','hermes'
)
ON CONFLICT (project_id, agent_id) DO NOTHING;
```

### 4) Seed shared state

```sql
WITH p AS (
  SELECT project_id FROM core.projects WHERE external_key = 'shared-agent-state'
),
a AS (
  SELECT agent_id FROM core.agents WHERE agent_key = 'agent-zero'
),
e AS (
  SELECT api.append_event(
    (SELECT project_id FROM p),
    (SELECT agent_id FROM a),
    'project.bootstrap',
    'project',
    'root',
    'bootstrap-v1',
    '{"note":"initial bootstrap"}'::jsonb
  ) AS event_id
)
SELECT api.upsert_core_state(
  (SELECT project_id FROM p),
  (SELECT agent_id FROM a),
  'project',
  'root',
  'objective',
  '{"goal":"create shared postgres state so agents coordinate deterministically"}'::jsonb,
  NULL,
  (SELECT event_id FROM e),
  1.0
);
```

---

## High-value read queries

### Project dashboard

```sql
SELECT
  p.project_id,
  p.project_name,
  p.status,
  COUNT(DISTINCT t.task_id) FILTER (WHERE t.status <> 'done') AS open_tasks,
  COUNT(DISTINCT h.handoff_id) FILTER (WHERE h.status = 'open') AS open_handoffs,
  MAX(ev.created_at) AS last_event_at
FROM core.projects p
LEFT JOIN shared.tasks t ON t.project_id = p.project_id
LEFT JOIN shared.handoffs h ON h.project_id = p.project_id
LEFT JOIN shared.events ev ON ev.project_id = p.project_id
GROUP BY 1,2,3;
```

### Current shared state by scope

```sql
SELECT scope_type, scope_key, state_key, value_json, value_text, row_version, updated_at
FROM shared.core_state
WHERE project_id = $1
ORDER BY scope_type, scope_key, state_key;
```

### Ready tasks

```sql
SELECT task_id, title, priority, assigned_agent_id, updated_at
FROM shared.tasks
WHERE project_id = $1
  AND status IN ('todo','blocked','review')
ORDER BY
  CASE priority
    WHEN 'critical' THEN 1
    WHEN 'high' THEN 2
    WHEN 'medium' THEN 3
    ELSE 4
  END,
  updated_at DESC;
```

### Open handoffs for one agent

```sql
SELECT h.handoff_id, h.subject, h.payload, fa.agent_key AS from_agent
FROM shared.handoffs h
LEFT JOIN core.agents fa ON fa.agent_id = h.from_agent_id
WHERE h.project_id = $1
  AND h.to_agent_id = $2
  AND h.status = 'open'
ORDER BY h.created_at ASC;
```

### Latest event stream

```sql
SELECT ev.event_id, ev.created_at, ag.agent_key, ev.event_type, ev.scope_type, ev.scope_key, ev.event_payload
FROM shared.events ev
LEFT JOIN core.agents ag ON ag.agent_id = ev.agent_id
WHERE ev.project_id = $1
ORDER BY ev.event_id DESC
LIMIT 200;
```

Because `jsonb` containment/key lookups benefit from GIN indexing, the event and state tables are set up to support structured querying without flattening everything into columns. ([PostgreSQL][3])

---

## Standard write flows

### A. Agent claims a task lease

```sql
SELECT api.claim_lease(
  p_project_id := $1,
  p_agent_id := $2,
  p_scope_type := 'task',
  p_scope_key := 'design-shared-schema',
  p_lease_reason := 'implementing schema',
  p_ttl_seconds := 1800
);
```

### B. Agent updates its extension state

```sql
SELECT api.upsert_agent_runtime_state(
  p_agent_key := 'claude-code',
  p_project_id := $1,
  p_workspace_root := '/repo',
  p_cwd := '/repo/db',
  p_active_branch := 'feat/shared-state',
  p_active_task_key := 'design-shared-schema',
  p_local_state := '{"editor":"vim","dirty_files":["db/schema.sql"]}'::jsonb,
  p_compact_memory := '{"last_summary":"designed core tables and triggers"}'::jsonb,
  p_pending_actions := '["write migration","run tests"]'::jsonb,
  p_last_prompt_digest := 'sha256:abc123',
  p_last_seen_event_id := 812
);
```

### C. Agent appends an event and updates shared state

```sql
WITH ev AS (
  SELECT api.append_event(
    $1, $2,
    'schema.draft.updated',
    'artifact',
    'db/schema.sql',
    'schema-draft-2026-04-23T10:15Z',
    '{"change":"added core/shared/ext/api schemas"}'::jsonb
  ) AS event_id
)
SELECT api.upsert_core_state(
  $1, $2,
  'project', 'root', 'db.schema.status',
  '{"state":"drafted","artifact":"db/schema.sql"}'::jsonb,
  'drafted',
  (SELECT event_id FROM ev),
  0.98
);
```

### D. Agent creates or updates a task

```sql
SELECT api.upsert_task(
  p_project_id := $1,
  p_title := 'Design shared schema',
  p_description := 'Create project/core/shared/ext/api schemas and deterministic write functions',
  p_status := 'in_progress',
  p_priority := 'critical',
  p_assigned_agent_id := $2,
  p_requested_by_agent_id := $3,
  p_depends_on := '[]'::jsonb,
  p_acceptance_criteria := '["DDL compiles","upserts are idempotent","leases enforce single writer per scope"]'::jsonb,
  p_task_metadata := '{"area":"database","milestone":"phase-1"}'::jsonb
);
```

### E. Agent records a decision

```sql
SELECT api.upsert_decision(
  p_project_id := $1,
  p_decision_key := 'event-sourced-current-state-hybrid',
  p_title := 'Use hybrid event log + current state tables',
  p_summary := 'Keep immutable events plus mutable current-state projections',
  p_rationale := 'Fast reads, complete audit history, easier reconciliation',
  p_chosen_option := '{"pattern":"hybrid"}'::jsonb,
  p_alternatives := '[{"pattern":"pure event sourcing"},{"pattern":"pure mutable tables"}]'::jsonb,
  p_made_by_agent_id := $2
);
```

### F. Agent produces an artifact

```sql
SELECT api.upsert_artifact(
  p_project_id := $1,
  p_artifact_type := 'migration',
  p_artifact_key := 'db/migrations/001_bootstrap.sql',
  p_location_uri := 'repo://db/migrations/001_bootstrap.sql',
  p_content_hash := 'sha256:...',
  p_version_label := 'v1',
  p_producer_agent_id := $2,
  p_artifact_metadata := '{"applies_to":"postgres","status":"draft"}'::jsonb
);
```

### G. Agent hands off to another agent

```sql
INSERT INTO shared.handoffs(
  project_id, from_agent_id, to_agent_id, handoff_kind, subject, payload
)
VALUES (
  $1, $2, $3, 'review',
  'Review bootstrap migration',
  '{"artifact":"db/migrations/001_bootstrap.sql","checks":["sql compiles","indexes correct","locks safe"]}'::jsonb
);
```

---

## Prompts

### 1) Universal DB contract prompt

```text
You are one agent in a multi-agent project system backed by PostgreSQL.

Rules:
1. Treat the database as the source of truth.
2. Before doing work, read:
   - core.projects
   - core.project_agents
   - shared.core_state
   - shared.tasks
   - shared.decisions
   - open shared.handoffs addressed to you
   - your ext.<agent>_state row
3. Never write directly to shared tables except through approved api.* functions.
4. Every meaningful write must:
   - append an event with a unique idempotency key
   - update current shared state, task, artifact, decision, or handoff
   - update your ext table row
5. If editing a task/file/branch scope, claim a lease first.
6. Prefer updating existing rows over creating duplicates:
   - task uniqueness is by canonical title per project
   - decision uniqueness is by decision_key per project
   - shared state uniqueness is by project_id + scope_type + scope_key + state_key
7. When uncertain, write a handoff or shared state note instead of inventing facts.
8. Keep payloads structured and machine-readable JSON.
```

### 2) Orchestrator prompt

```text
Role: orchestrator.

Objectives:
- keep project objectives, task queue, and cross-agent coordination coherent
- resolve duplicate tasks
- ensure every important milestone is represented by:
  1. an event
  2. a task/decision/artifact row
  3. updated shared.core_state

Workflow:
- inspect open tasks, open handoffs, active leases, and recent events
- assign or rebalance tasks
- write decisions when architecture changes
- expire stale assumptions by setting expires_at in shared.core_state when appropriate
- require explicit acceptance criteria on all critical tasks
```

### 3) Worker prompt

```text
Role: implementer.

Workflow:
- read project objective and current task
- claim lease on the task or file scope
- update your ext state before and after work
- append an event for each milestone
- upsert artifacts produced
- mark task status accurately
- if blocked, create/update a handoff instead of silently stalling
```

### 4) Reviewer prompt

```text
Role: reviewer.

Workflow:
- read artifact, related task, related decision, and recent events
- do not rewrite history; append review events
- if accepted, update task to review/done and create any follow-up tasks deterministically
- if rejected, add a structured handoff with explicit findings and required fixes
```

### 5) Memory/summarizer prompt

```text
Role: memory keeper.

Workflow:
- compress long event streams into compact_memory and shared.core_state summaries
- never replace precise state with vague summaries
- update:
  - project.summary.current
  - architecture.summary.current
  - blockers.current
  - next-actions.current
- keep summaries anchored to artifact keys, decision keys, and task canonical titles
```

---

## Recommended persisted context beyond the minimum

Add these shared state keys early:

* `project/root/objective`
* `project/root/definition_of_done`
* `project/root/active_branch`
* `project/root/repo_layout`
* `project/root/testing_strategy`
* `project/root/deployment_strategy`
* `project/root/blockers.current`
* `project/root/next_actions.current`
* `project/root/architecture.summary.current`

Useful extra scope types:

* `file`
* `branch`
* `service`
* `api`
* `migration`
* `prompt`
* `environment`

---

## Minimal operating protocol for every agent run

```text
1. Resolve project_id and agent_id.
2. Read current state + your extension row.
3. Claim lease if touching a scoped resource.
4. Perform work.
5. append_event(...)
6. upsert_core_state(...) and/or upsert_task(...) / upsert_decision(...) / upsert_artifact(...)
7. upsert_agent_runtime_state(...)
8. create handoff if another agent should continue.
9. release lease.
```

---

## What this gives you

* multiple projects
* shared project memory
* deterministic current state
* append-only history
* agent-specific runtime memory
* collision control via leases + advisory locks
* idempotent upserts
* structured handoffs
* auditability

If you want, I can turn this into a single production-ready migration set with seed data, views, and a thin TypeScript query layer.

[1]: https://www.postgresql.org/docs/current/ddl-identity-columns.html?utm_source=chatgpt.com "Documentation: 18: 5.3. Identity Columns"
[2]: https://www.postgresql.org/docs/current/ddl-generated-columns.html?utm_source=chatgpt.com "Documentation: 18: 5.4. Generated Columns"
[3]: https://www.postgresql.org/docs/current/gin.html?utm_source=chatgpt.com "Documentation: 18: 65.4. GIN Indexes"
