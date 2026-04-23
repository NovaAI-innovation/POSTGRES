# Database Schema Documentation

Generated: 2026-04-23 10:58:56 -06:00

Database: `ai_suite`
Host: `76.13.103.104`

## Schemas
```text
 schema_name 
-------------
 api
 core
 ext
 public
 shared
(5 rows)

```

## Object Summary by Schema
```text
 schema_name | tables | views | materialized_views | sequences 
-------------+--------+-------+--------------------+-----------
 api         |      0 |     1 |                  0 |         0
 core        |      3 |     0 |                  0 |         2
 ext         |      7 |     0 |                  0 |         0
 shared      |      7 |     0 |                  0 |         7
(4 rows)

```

## Tables
```text
 schema_name |     table_name     | table_type | table_comment | est_live_rows 
-------------+--------------------+------------+---------------+---------------
 core        | agents             | table      |               |             6
 core        | project_agents     | table      |               |             6
 core        | projects           | table      |               |             1
 ext         | agent_runtime_base | table      |               |             0
 ext         | agent_zero_state   | table      |               |             0
 ext         | claude_code_state  | table      |               |             1
 ext         | gemini_cli_state   | table      |               |             0
 ext         | hermes_state       | table      |               |             0
 ext         | openai_codex_state | table      |               |             1
 ext         | openclaw_state     | table      |               |             0
 shared      | agent_leases       | table      |               |             5
 shared      | artifacts          | table      |               |             0
 shared      | core_state         | table      |               |             6
 shared      | decisions          | table      |               |             0
 shared      | events             | table      |               |            10
 shared      | handoffs           | table      |               |             0
 shared      | tasks              | table      |               |             0
(17 rows)

```

## Columns
```text
 table_schema |     table_name     | ordinal_position |      column_name       |        data_type         |  udt_name   | is_nullable |  column_default   | character_maximum_length | numeric_precision | numeric_scale | datetime_precision 
--------------+--------------------+------------------+------------------------+--------------------------+-------------+-------------+-------------------+--------------------------+-------------------+---------------+--------------------
 api          | project_summary    |                1 | project_id             | bigint                   | int8        | YES         |                   |                          |                64 |             0 |                   
 api          | project_summary    |                2 | project_name           | text                     | text        | YES         |                   |                          |                   |               |                   
 api          | project_summary    |                3 | project_slug           | text                     | text        | YES         |                   |                          |                   |               |                   
 api          | project_summary    |                4 | status                 | text                     | text        | YES         |                   |                          |                   |               |                   
 api          | project_summary    |                5 | default_branch         | text                     | text        | YES         |                   |                          |                   |               |                   
 api          | project_summary    |                6 | repo_url               | text                     | text        | YES         |                   |                          |                   |               |                   
 api          | project_summary    |                7 | agent_count            | bigint                   | int8        | YES         |                   |                          |                64 |             0 |                   
 api          | project_summary    |                8 | open_tasks             | bigint                   | int8        | YES         |                   |                          |                64 |             0 |                   
 api          | project_summary    |                9 | done_tasks             | bigint                   | int8        | YES         |                   |                          |                64 |             0 |                   
 api          | project_summary    |               10 | open_handoffs          | bigint                   | int8        | YES         |                   |                          |                64 |             0 |                   
 api          | project_summary    |               11 | decision_count         | bigint                   | int8        | YES         |                   |                          |                64 |             0 |                   
 api          | project_summary    |               12 | artifact_count         | bigint                   | int8        | YES         |                   |                          |                64 |             0 |                   
 api          | project_summary    |               13 | last_event_at          | timestamp with time zone | timestamptz | YES         |                   |                          |                   |               |                  6
 api          | project_summary    |               14 | created_at             | timestamp with time zone | timestamptz | YES         |                   |                          |                   |               |                  6
 api          | project_summary    |               15 | updated_at             | timestamp with time zone | timestamptz | YES         |                   |                          |                   |               |                  6
 core         | agents             |                1 | agent_id               | bigint                   | int8        | NO          |                   |                          |                64 |             0 |                   
 core         | agents             |                2 | agent_key              | text                     | text        | NO          |                   |                          |                   |               |                   
 core         | agents             |                3 | agent_family           | text                     | text        | NO          |                   |                          |                   |               |                   
 core         | agents             |                4 | display_name           | text                     | text        | NO          |                   |                          |                   |               |                   
 core         | agents             |                5 | model_hint             | text                     | text        | YES         |                   |                          |                   |               |                   
 core         | agents             |                6 | capabilities           | jsonb                    | jsonb       | NO          | '[]'::jsonb       |                          |                   |               |                   
 core         | agents             |                7 | config                 | jsonb                    | jsonb       | NO          | '{}'::jsonb       |                          |                   |               |                   
 core         | agents             |                8 | is_active              | boolean                  | bool        | NO          | true              |                          |                   |               |                   
 core         | agents             |                9 | row_version            | bigint                   | int8        | NO          | 1                 |                          |                64 |             0 |                   
 core         | agents             |               10 | created_at             | timestamp with time zone | timestamptz | NO          | now()             |                          |                   |               |                  6
 core         | agents             |               11 | updated_at             | timestamp with time zone | timestamptz | NO          | now()             |                          |                   |               |                  6
 core         | project_agents     |                1 | project_id             | bigint                   | int8        | NO          |                   |                          |                64 |             0 |                   
 core         | project_agents     |                2 | agent_id               | bigint                   | int8        | NO          |                   |                          |                64 |             0 |                   
 core         | project_agents     |                3 | role_name              | text                     | text        | NO          | 'worker'::text    |                          |                   |               |                   
 core         | project_agents     |                4 | can_write_shared       | boolean                  | bool        | NO          | true              |                          |                   |               |                   
 core         | project_agents     |                5 | priority_weight        | integer                  | int4        | NO          | 100               |                          |                32 |             0 |                   
 core         | project_agents     |                6 | membership_metadata    | jsonb                    | jsonb       | NO          | '{}'::jsonb       |                          |                   |               |                   
 core         | project_agents     |                7 | row_version            | bigint                   | int8        | NO          | 1                 |                          |                64 |             0 |                   
 core         | project_agents     |                8 | created_at             | timestamp with time zone | timestamptz | NO          | now()             |                          |                   |               |                  6
 core         | project_agents     |                9 | updated_at             | timestamp with time zone | timestamptz | NO          | now()             |                          |                   |               |                  6
 core         | projects           |                1 | project_id             | bigint                   | int8        | NO          |                   |                          |                64 |             0 |                   
 core         | projects           |                2 | external_key           | text                     | text        | NO          |                   |                          |                   |               |                   
 core         | projects           |                3 | project_name           | text                     | text        | NO          |                   |                          |                   |               |                   
 core         | projects           |                4 | project_slug           | text                     | text        | YES         |                   |                          |                   |               |                   
 core         | projects           |                5 | status                 | text                     | text        | NO          | 'active'::text    |                          |                   |               |                   
 core         | projects           |                6 | default_branch         | text                     | text        | YES         |                   |                          |                   |               |                   
 core         | projects           |                7 | repo_url               | text                     | text        | YES         |                   |                          |                   |               |                   
 core         | projects           |                8 | metadata               | jsonb                    | jsonb       | NO          | '{}'::jsonb       |                          |                   |               |                   
 core         | projects           |                9 | row_version            | bigint                   | int8        | NO          | 1                 |                          |                64 |             0 |                   
 core         | projects           |               10 | created_at             | timestamp with time zone | timestamptz | NO          | now()             |                          |                   |               |                  6
 core         | projects           |               11 | updated_at             | timestamp with time zone | timestamptz | NO          | now()             |                          |                   |               |                  6
 ext          | agent_runtime_base |                1 | project_id             | bigint                   | int8        | NO          |                   |                          |                64 |             0 |                   
 ext          | agent_runtime_base |                2 | agent_id               | bigint                   | int8        | NO          |                   |                          |                64 |             0 |                   
 ext          | agent_runtime_base |                3 | workspace_root         | text                     | text        | YES         |                   |                          |                   |               |                   
 ext          | agent_runtime_base |                4 | cwd                    | text                     | text        | YES         |                   |                          |                   |               |                   
 ext          | agent_runtime_base |                5 | active_branch          | text                     | text        | YES         |                   |                          |                   |               |                   
 ext          | agent_runtime_base |                6 | active_task_key        | text                     | text        | YES         |                   |                          |                   |               |                   
 ext          | agent_runtime_base |                7 | local_state            | jsonb                    | jsonb       | NO          | '{}'::jsonb       |                          |                   |               |                   
 ext          | agent_runtime_base |                8 | compact_memory         | jsonb                    | jsonb       | NO          | '{}'::jsonb       |                          |                   |               |                   
 ext          | agent_runtime_base |                9 | pending_actions        | jsonb                    | jsonb       | NO          | '[]'::jsonb       |                          |                   |               |                   
 ext          | agent_runtime_base |               10 | last_prompt_digest     | text                     | text        | YES         |                   |                          |                   |               |                   
 ext          | agent_runtime_base |               11 | last_seen_event_id     | bigint                   | int8        | YES         |                   |                          |                64 |             0 |                   
 ext          | agent_runtime_base |               12 | row_version            | bigint                   | int8        | NO          | 1                 |                          |                64 |             0 |                   
 ext          | agent_runtime_base |               13 | created_at             | timestamp with time zone | timestamptz | NO          | now()             |                          |                   |               |                  6
 ext          | agent_runtime_base |               14 | updated_at             | timestamp with time zone | timestamptz | NO          | now()             |                          |                   |               |                  6
 ext          | agent_zero_state   |                1 | project_id             | bigint                   | int8        | NO          |                   |                          |                64 |             0 |                   
 ext          | agent_zero_state   |                2 | agent_id               | bigint                   | int8        | NO          |                   |                          |                64 |             0 |                   
 ext          | agent_zero_state   |                3 | workspace_root         | text                     | text        | YES         |                   |                          |                   |               |                   
 ext          | agent_zero_state   |                4 | cwd                    | text                     | text        | YES         |                   |                          |                   |               |                   
 ext          | agent_zero_state   |                5 | active_branch          | text                     | text        | YES         |                   |                          |                   |               |                   
 ext          | agent_zero_state   |                6 | active_task_key        | text                     | text        | YES         |                   |                          |                   |               |                   
 ext          | agent_zero_state   |                7 | local_state            | jsonb                    | jsonb       | NO          | '{}'::jsonb       |                          |                   |               |                   
 ext          | agent_zero_state   |                8 | compact_memory         | jsonb                    | jsonb       | NO          | '{}'::jsonb       |                          |                   |               |                   
 ext          | agent_zero_state   |                9 | pending_actions        | jsonb                    | jsonb       | NO          | '[]'::jsonb       |                          |                   |               |                   
 ext          | agent_zero_state   |               10 | last_prompt_digest     | text                     | text        | YES         |                   |                          |                   |               |                   
 ext          | agent_zero_state   |               11 | last_seen_event_id     | bigint                   | int8        | YES         |                   |                          |                64 |             0 |                   
 ext          | agent_zero_state   |               12 | row_version            | bigint                   | int8        | NO          | 1                 |                          |                64 |             0 |                   
 ext          | agent_zero_state   |               13 | created_at             | timestamp with time zone | timestamptz | NO          | now()             |                          |                   |               |                  6
 ext          | agent_zero_state   |               14 | updated_at             | timestamp with time zone | timestamptz | NO          | now()             |                          |                   |               |                  6
 ext          | agent_zero_state   |               15 | planner_state          | jsonb                    | jsonb       | NO          | '{}'::jsonb       |                          |                   |               |                   
 ext          | claude_code_state  |                1 | project_id             | bigint                   | int8        | NO          |                   |                          |                64 |             0 |                   
 ext          | claude_code_state  |                2 | agent_id               | bigint                   | int8        | NO          |                   |                          |                64 |             0 |                   
 ext          | claude_code_state  |                3 | workspace_root         | text                     | text        | YES         |                   |                          |                   |               |                   
 ext          | claude_code_state  |                4 | cwd                    | text                     | text        | YES         |                   |                          |                   |               |                   
 ext          | claude_code_state  |                5 | active_branch          | text                     | text        | YES         |                   |                          |                   |               |                   
 ext          | claude_code_state  |                6 | active_task_key        | text                     | text        | YES         |                   |                          |                   |               |                   
 ext          | claude_code_state  |                7 | local_state            | jsonb                    | jsonb       | NO          | '{}'::jsonb       |                          |                   |               |                   
 ext          | claude_code_state  |                8 | compact_memory         | jsonb                    | jsonb       | NO          | '{}'::jsonb       |                          |                   |               |                   
 ext          | claude_code_state  |                9 | pending_actions        | jsonb                    | jsonb       | NO          | '[]'::jsonb       |                          |                   |               |                   
 ext          | claude_code_state  |               10 | last_prompt_digest     | text                     | text        | YES         |                   |                          |                   |               |                   
 ext          | claude_code_state  |               11 | last_seen_event_id     | bigint                   | int8        | YES         |                   |                          |                64 |             0 |                   
 ext          | claude_code_state  |               12 | row_version            | bigint                   | int8        | NO          | 1                 |                          |                64 |             0 |                   
 ext          | claude_code_state  |               13 | created_at             | timestamp with time zone | timestamptz | NO          | now()             |                          |                   |               |                  6
 ext          | claude_code_state  |               14 | updated_at             | timestamp with time zone | timestamptz | NO          | now()             |                          |                   |               |                  6
 ext          | claude_code_state  |               15 | session_transcript_ref | text                     | text        | YES         |                   |                          |                   |               |                   
 ext          | claude_code_state  |               16 | patch_queue            | jsonb                    | jsonb       | NO          | '[]'::jsonb       |                          |                   |               |                   
 ext          | gemini_cli_state   |                1 | project_id             | bigint                   | int8        | NO          |                   |                          |                64 |             0 |                   
 ext          | gemini_cli_state   |                2 | agent_id               | bigint                   | int8        | NO          |                   |                          |                64 |             0 |                   
 ext          | gemini_cli_state   |                3 | workspace_root         | text                     | text        | YES         |                   |                          |                   |               |                   
 ext          | gemini_cli_state   |                4 | cwd                    | text                     | text        | YES         |                   |                          |                   |               |                   
 ext          | gemini_cli_state   |                5 | active_branch          | text                     | text        | YES         |                   |                          |                   |               |                   
 ext          | gemini_cli_state   |                6 | active_task_key        | text                     | text        | YES         |                   |                          |                   |               |                   
 ext          | gemini_cli_state   |                7 | local_state            | jsonb                    | jsonb       | NO          | '{}'::jsonb       |                          |                   |               |                   
 ext          | gemini_cli_state   |                8 | compact_memory         | jsonb                    | jsonb       | NO          | '{}'::jsonb       |                          |                   |               |                   
 ext          | gemini_cli_state   |                9 | pending_actions        | jsonb                    | jsonb       | NO          | '[]'::jsonb       |                          |                   |               |                   
 ext          | gemini_cli_state   |               10 | last_prompt_digest     | text                     | text        | YES         |                   |                          |                   |               |                   
 ext          | gemini_cli_state   |               11 | last_seen_event_id     | bigint                   | int8        | YES         |                   |                          |                64 |             0 |                   
 ext          | gemini_cli_state   |               12 | row_version            | bigint                   | int8        | NO          | 1                 |                          |                64 |             0 |                   
 ext          | gemini_cli_state   |               13 | created_at             | timestamp with time zone | timestamptz | NO          | now()             |                          |                   |               |                  6
 ext          | gemini_cli_state   |               14 | updated_at             | timestamp with time zone | timestamptz | NO          | now()             |                          |                   |               |                  6
 ext          | gemini_cli_state   |               15 | notebook_context       | jsonb                    | jsonb       | NO          | '{}'::jsonb       |                          |                   |               |                   
 ext          | hermes_state       |                1 | project_id             | bigint                   | int8        | NO          |                   |                          |                64 |             0 |                   
 ext          | hermes_state       |                2 | agent_id               | bigint                   | int8        | NO          |                   |                          |                64 |             0 |                   
 ext          | hermes_state       |                3 | workspace_root         | text                     | text        | YES         |                   |                          |                   |               |                   
 ext          | hermes_state       |                4 | cwd                    | text                     | text        | YES         |                   |                          |                   |               |                   
 ext          | hermes_state       |                5 | active_branch          | text                     | text        | YES         |                   |                          |                   |               |                   
 ext          | hermes_state       |                6 | active_task_key        | text                     | text        | YES         |                   |                          |                   |               |                   
 ext          | hermes_state       |                7 | local_state            | jsonb                    | jsonb       | NO          | '{}'::jsonb       |                          |                   |               |                   
 ext          | hermes_state       |                8 | compact_memory         | jsonb                    | jsonb       | NO          | '{}'::jsonb       |                          |                   |               |                   
 ext          | hermes_state       |                9 | pending_actions        | jsonb                    | jsonb       | NO          | '[]'::jsonb       |                          |                   |               |                   
 ext          | hermes_state       |               10 | last_prompt_digest     | text                     | text        | YES         |                   |                          |                   |               |                   
 ext          | hermes_state       |               11 | last_seen_event_id     | bigint                   | int8        | YES         |                   |                          |                64 |             0 |                   
 ext          | hermes_state       |               12 | row_version            | bigint                   | int8        | NO          | 1                 |                          |                64 |             0 |                   
 ext          | hermes_state       |               13 | created_at             | timestamp with time zone | timestamptz | NO          | now()             |                          |                   |               |                  6
 ext          | hermes_state       |               14 | updated_at             | timestamp with time zone | timestamptz | NO          | now()             |                          |                   |               |                  6
 ext          | hermes_state       |               15 | memory_threads         | jsonb                    | jsonb       | NO          | '[]'::jsonb       |                          |                   |               |                   
 ext          | openai_codex_state |                1 | project_id             | bigint                   | int8        | NO          |                   |                          |                64 |             0 |                   
 ext          | openai_codex_state |                2 | agent_id               | bigint                   | int8        | NO          |                   |                          |                64 |             0 |                   
 ext          | openai_codex_state |                3 | workspace_root         | text                     | text        | YES         |                   |                          |                   |               |                   
 ext          | openai_codex_state |                4 | cwd                    | text                     | text        | YES         |                   |                          |                   |               |                   
 ext          | openai_codex_state |                5 | active_branch          | text                     | text        | YES         |                   |                          |                   |               |                   
 ext          | openai_codex_state |                6 | active_task_key        | text                     | text        | YES         |                   |                          |                   |               |                   
 ext          | openai_codex_state |                7 | local_state            | jsonb                    | jsonb       | NO          | '{}'::jsonb       |                          |                   |               |                   
 ext          | openai_codex_state |                8 | compact_memory         | jsonb                    | jsonb       | NO          | '{}'::jsonb       |                          |                   |               |                   
 ext          | openai_codex_state |                9 | pending_actions        | jsonb                    | jsonb       | NO          | '[]'::jsonb       |                          |                   |               |                   
 ext          | openai_codex_state |               10 | last_prompt_digest     | text                     | text        | YES         |                   |                          |                   |               |                   
 ext          | openai_codex_state |               11 | last_seen_event_id     | bigint                   | int8        | YES         |                   |                          |                64 |             0 |                   
 ext          | openai_codex_state |               12 | row_version            | bigint                   | int8        | NO          | 1                 |                          |                64 |             0 |                   
 ext          | openai_codex_state |               13 | created_at             | timestamp with time zone | timestamptz | NO          | now()             |                          |                   |               |                  6
 ext          | openai_codex_state |               14 | updated_at             | timestamp with time zone | timestamptz | NO          | now()             |                          |                   |               |                  6
 ext          | openai_codex_state |               15 | code_review_queue      | jsonb                    | jsonb       | NO          | '[]'::jsonb       |                          |                   |               |                   
 ext          | openclaw_state     |                1 | project_id             | bigint                   | int8        | NO          |                   |                          |                64 |             0 |                   
 ext          | openclaw_state     |                2 | agent_id               | bigint                   | int8        | NO          |                   |                          |                64 |             0 |                   
 ext          | openclaw_state     |                3 | workspace_root         | text                     | text        | YES         |                   |                          |                   |               |                   
 ext          | openclaw_state     |                4 | cwd                    | text                     | text        | YES         |                   |                          |                   |               |                   
 ext          | openclaw_state     |                5 | active_branch          | text                     | text        | YES         |                   |                          |                   |               |                   
 ext          | openclaw_state     |                6 | active_task_key        | text                     | text        | YES         |                   |                          |                   |               |                   
 ext          | openclaw_state     |                7 | local_state            | jsonb                    | jsonb       | NO          | '{}'::jsonb       |                          |                   |               |                   
 ext          | openclaw_state     |                8 | compact_memory         | jsonb                    | jsonb       | NO          | '{}'::jsonb       |                          |                   |               |                   
 ext          | openclaw_state     |                9 | pending_actions        | jsonb                    | jsonb       | NO          | '[]'::jsonb       |                          |                   |               |                   
 ext          | openclaw_state     |               10 | last_prompt_digest     | text                     | text        | YES         |                   |                          |                   |               |                   
 ext          | openclaw_state     |               11 | last_seen_event_id     | bigint                   | int8        | YES         |                   |                          |                64 |             0 |                   
 ext          | openclaw_state     |               12 | row_version            | bigint                   | int8        | NO          | 1                 |                          |                64 |             0 |                   
 ext          | openclaw_state     |               13 | created_at             | timestamp with time zone | timestamptz | NO          | now()             |                          |                   |               |                  6
 ext          | openclaw_state     |               14 | updated_at             | timestamp with time zone | timestamptz | NO          | now()             |                          |                   |               |                  6
 ext          | openclaw_state     |               15 | toolchain_state        | jsonb                    | jsonb       | NO          | '{}'::jsonb       |                          |                   |               |                   
 shared       | agent_leases       |                1 | lease_id               | bigint                   | int8        | NO          |                   |                          |                64 |             0 |                   
 shared       | agent_leases       |                2 | project_id             | bigint                   | int8        | NO          |                   |                          |                64 |             0 |                   
 shared       | agent_leases       |                3 | agent_id               | bigint                   | int8        | NO          |                   |                          |                64 |             0 |                   
 shared       | agent_leases       |                4 | lease_scope_type       | text                     | text        | NO          |                   |                          |                   |               |                   
 shared       | agent_leases       |                5 | lease_scope_key        | text                     | text        | NO          | ''::text          |                          |                   |               |                   
 shared       | agent_leases       |                6 | lease_reason           | text                     | text        | NO          |                   |                          |                   |               |                   
 shared       | agent_leases       |                7 | lease_token            | uuid                     | uuid        | NO          | gen_random_uuid() |                          |                   |               |                   
 shared       | agent_leases       |                8 | acquired_at            | timestamp with time zone | timestamptz | NO          | now()             |                          |                   |               |                  6
 shared       | agent_leases       |                9 | expires_at             | timestamp with time zone | timestamptz | NO          |                   |                          |                   |               |                  6
 shared       | agent_leases       |               10 | released_at            | timestamp with time zone | timestamptz | YES         |                   |                          |                   |               |                  6
 shared       | artifacts          |                1 | artifact_id            | bigint                   | int8        | NO          |                   |                          |                64 |             0 |                   
 shared       | artifacts          |                2 | project_id             | bigint                   | int8        | NO          |                   |                          |                64 |             0 |                   
 shared       | artifacts          |                3 | artifact_type          | text                     | text        | NO          |                   |                          |                   |               |                   
 shared       | artifacts          |                4 | artifact_key           | text                     | text        | NO          |                   |                          |                   |               |                   
 shared       | artifacts          |                5 | location_uri           | text                     | text        | YES         |                   |                          |                   |               |                   
 shared       | artifacts          |                6 | content_hash           | text                     | text        | YES         |                   |                          |                   |               |                   
 shared       | artifacts          |                7 | version_label          | text                     | text        | YES         |                   |                          |                   |               |                   
 shared       | artifacts          |                8 | producer_agent_id      | bigint                   | int8        | YES         |                   |                          |                64 |             0 |                   
 shared       | artifacts          |                9 | artifact_metadata      | jsonb                    | jsonb       | NO          | '{}'::jsonb       |                          |                   |               |                   
 shared       | artifacts          |               10 | row_version            | bigint                   | int8        | NO          | 1                 |                          |                64 |             0 |                   
 shared       | artifacts          |               11 | created_at             | timestamp with time zone | timestamptz | NO          | now()             |                          |                   |               |                  6
 shared       | artifacts          |               12 | updated_at             | timestamp with time zone | timestamptz | NO          | now()             |                          |                   |               |                  6
 shared       | core_state         |                1 | state_id               | bigint                   | int8        | NO          |                   |                          |                64 |             0 |                   
 shared       | core_state         |                2 | project_id             | bigint                   | int8        | YES         |                   |                          |                64 |             0 |                   
 shared       | core_state         |                3 | scope_type             | text                     | text        | NO          |                   |                          |                   |               |                   
 shared       | core_state         |                4 | scope_key              | text                     | text        | NO          | ''::text          |                          |                   |               |                   
 shared       | core_state         |                5 | state_key              | text                     | text        | NO          |                   |                          |                   |               |                   
 shared       | core_state         |                6 | value_json             | jsonb                    | jsonb       | NO          | '{}'::jsonb       |                          |                   |               |                   
 shared       | core_state         |                7 | value_text             | text                     | text        | YES         |                   |                          |                   |               |                   
 shared       | core_state         |                8 | source_event_id        | bigint                   | int8        | YES         |                   |                          |                64 |             0 |                   
 shared       | core_state         |                9 | source_agent_id        | bigint                   | int8        | YES         |                   |                          |                64 |             0 |                   
 shared       | core_state         |               10 | confidence             | numeric                  | numeric     | YES         |                   |                          |                 5 |             4 |                   
 shared       | core_state         |               11 | effective_at           | timestamp with time zone | timestamptz | NO          | now()             |                          |                   |               |                  6
 shared       | core_state         |               12 | expires_at             | timestamp with time zone | timestamptz | YES         |                   |                          |                   |               |                  6
 shared       | core_state         |               13 | row_version            | bigint                   | int8        | NO          | 1                 |                          |                64 |             0 |                   
 shared       | core_state         |               14 | created_at             | timestamp with time zone | timestamptz | NO          | now()             |                          |                   |               |                  6
 shared       | core_state         |               15 | updated_at             | timestamp with time zone | timestamptz | NO          | now()             |                          |                   |               |                  6
 shared       | decisions          |                1 | decision_id            | bigint                   | int8        | NO          |                   |                          |                64 |             0 |                   
 shared       | decisions          |                2 | project_id             | bigint                   | int8        | NO          |                   |                          |                64 |             0 |                   
 shared       | decisions          |                3 | decision_key           | text                     | text        | NO          |                   |                          |                   |               |                   
 shared       | decisions          |                4 | title                  | text                     | text        | NO          |                   |                          |                   |               |                   
 shared       | decisions          |                5 | summary                | text                     | text        | NO          |                   |                          |                   |               |                   
 shared       | decisions          |                6 | rationale              | text                     | text        | YES         |                   |                          |                   |               |                   
 shared       | decisions          |                7 | chosen_option          | jsonb                    | jsonb       | NO          | '{}'::jsonb       |                          |                   |               |                   
 shared       | decisions          |                8 | alternatives           | jsonb                    | jsonb       | NO          | '[]'::jsonb       |                          |                   |               |                   
 shared       | decisions          |                9 | supersedes_decision_id | bigint                   | int8        | YES         |                   |                          |                64 |             0 |                   
 shared       | decisions          |               10 | made_by_agent_id       | bigint                   | int8        | YES         |                   |                          |                64 |             0 |                   
 shared       | decisions          |               11 | row_version            | bigint                   | int8        | NO          | 1                 |                          |                64 |             0 |                   
 shared       | decisions          |               12 | created_at             | timestamp with time zone | timestamptz | NO          | now()             |                          |                   |               |                  6
 shared       | decisions          |               13 | updated_at             | timestamp with time zone | timestamptz | NO          | now()             |                          |                   |               |                  6
 shared       | events             |                1 | event_id               | bigint                   | int8        | NO          |                   |                          |                64 |             0 |                   
 shared       | events             |                2 | project_id             | bigint                   | int8        | NO          |                   |                          |                64 |             0 |                   
 shared       | events             |                3 | agent_id               | bigint                   | int8        | YES         |                   |                          |                64 |             0 |                   
 shared       | events             |                4 | event_type             | text                     | text        | NO          |                   |                          |                   |               |                   
 shared       | events             |                5 | scope_type             | text                     | text        | NO          |                   |                          |                   |               |                   
 shared       | events             |                6 | scope_key              | text                     | text        | NO          | ''::text          |                          |                   |               |                   
 shared       | events             |                7 | idempotency_key        | text                     | text        | NO          |                   |                          |                   |               |                   
 shared       | events             |                8 | event_payload          | jsonb                    | jsonb       | NO          | '{}'::jsonb       |                          |                   |               |                   
 shared       | events             |                9 | created_at             | timestamp with time zone | timestamptz | NO          | now()             |                          |                   |               |                  6
 shared       | handoffs           |                1 | handoff_id             | bigint                   | int8        | NO          |                   |                          |                64 |             0 |                   
 shared       | handoffs           |                2 | project_id             | bigint                   | int8        | NO          |                   |                          |                64 |             0 |                   
 shared       | handoffs           |                3 | from_agent_id          | bigint                   | int8        | YES         |                   |                          |                64 |             0 |                   
 shared       | handoffs           |                4 | to_agent_id            | bigint                   | int8        | YES         |                   |                          |                64 |             0 |                   
 shared       | handoffs           |                5 | handoff_kind           | text                     | text        | NO          | 'work'::text      |                          |                   |               |                   
 shared       | handoffs           |                6 | status                 | text                     | text        | NO          | 'open'::text      |                          |                   |               |                   
 shared       | handoffs           |                7 | subject                | text                     | text        | NO          |                   |                          |                   |               |                   
 shared       | handoffs           |                8 | payload                | jsonb                    | jsonb       | NO          | '{}'::jsonb       |                          |                   |               |                   
 shared       | handoffs           |                9 | created_at             | timestamp with time zone | timestamptz | NO          | now()             |                          |                   |               |                  6
 shared       | handoffs           |               10 | updated_at             | timestamp with time zone | timestamptz | NO          | now()             |                          |                   |               |                  6
 shared       | tasks              |                1 | task_id                | bigint                   | int8        | NO          |                   |                          |                64 |             0 |                   
 shared       | tasks              |                2 | project_id             | bigint                   | int8        | NO          |                   |                          |                64 |             0 |                   
 shared       | tasks              |                3 | parent_task_id         | bigint                   | int8        | YES         |                   |                          |                64 |             0 |                   
 shared       | tasks              |                4 | canonical_title        | text                     | text        | NO          |                   |                          |                   |               |                   
 shared       | tasks              |                5 | title                  | text                     | text        | NO          |                   |                          |                   |               |                   
 shared       | tasks              |                6 | description            | text                     | text        | YES         |                   |                          |                   |               |                   
 shared       | tasks              |                7 | status                 | text                     | text        | NO          | 'todo'::text      |                          |                   |               |                   
 shared       | tasks              |                8 | priority               | text                     | text        | NO          | 'medium'::text    |                          |                   |               |                   
 shared       | tasks              |                9 | assigned_agent_id      | bigint                   | int8        | YES         |                   |                          |                64 |             0 |                   
 shared       | tasks              |               10 | requested_by_agent_id  | bigint                   | int8        | YES         |                   |                          |                64 |             0 |                   
 shared       | tasks              |               11 | depends_on             | jsonb                    | jsonb       | NO          | '[]'::jsonb       |                          |                   |               |                   
 shared       | tasks              |               12 | acceptance_criteria    | jsonb                    | jsonb       | NO          | '[]'::jsonb       |                          |                   |               |                   
 shared       | tasks              |               13 | task_metadata          | jsonb                    | jsonb       | NO          | '{}'::jsonb       |                          |                   |               |                   
 shared       | tasks              |               14 | row_version            | bigint                   | int8        | NO          | 1                 |                          |                64 |             0 |                   
 shared       | tasks              |               15 | created_at             | timestamp with time zone | timestamptz | NO          | now()             |                          |                   |               |                  6
 shared       | tasks              |               16 | updated_at             | timestamp with time zone | timestamptz | NO          | now()             |                          |                   |               |                  6
(236 rows)

```

## Constraints
```text
 table_schema |     table_name     |                         constraint_name                         | constraint_type |                                                            definition                                                             
--------------+--------------------+-----------------------------------------------------------------+-----------------+-----------------------------------------------------------------------------------------------------------------------------------
 core         | agents             | agents_pkey                                                     | PRIMARY KEY     | PRIMARY KEY (agent_id)
 core         | agents             | agents_agent_key_key                                            | UNIQUE          | UNIQUE (agent_key)
 core         | project_agents     | project_agents_agent_id_fkey                                    | FOREIGN KEY     | FOREIGN KEY (agent_id) REFERENCES core.agents(agent_id) ON DELETE CASCADE
 core         | project_agents     | project_agents_project_id_fkey                                  | FOREIGN KEY     | FOREIGN KEY (project_id) REFERENCES core.projects(project_id) ON DELETE CASCADE
 core         | project_agents     | project_agents_pkey                                             | PRIMARY KEY     | PRIMARY KEY (project_id, agent_id)
 core         | projects           | projects_status_check                                           | CHECK           | CHECK (status = ANY (ARRAY['active'::text, 'paused'::text, 'archived'::text, 'completed'::text]))
 core         | projects           | projects_pkey                                                   | PRIMARY KEY     | PRIMARY KEY (project_id)
 core         | projects           | projects_external_key_key                                       | UNIQUE          | UNIQUE (external_key)
 ext          | agent_runtime_base | agent_runtime_base_agent_id_fkey                                | FOREIGN KEY     | FOREIGN KEY (agent_id) REFERENCES core.agents(agent_id) ON DELETE CASCADE
 ext          | agent_runtime_base | agent_runtime_base_last_seen_event_id_fkey                      | FOREIGN KEY     | FOREIGN KEY (last_seen_event_id) REFERENCES shared.events(event_id) ON DELETE SET NULL
 ext          | agent_runtime_base | agent_runtime_base_project_id_fkey                              | FOREIGN KEY     | FOREIGN KEY (project_id) REFERENCES core.projects(project_id) ON DELETE CASCADE
 ext          | agent_runtime_base | agent_runtime_base_pkey                                         | PRIMARY KEY     | PRIMARY KEY (project_id, agent_id)
 ext          | agent_zero_state   | agent_zero_state_pkey                                           | PRIMARY KEY     | PRIMARY KEY (project_id, agent_id)
 ext          | claude_code_state  | claude_code_state_pkey                                          | PRIMARY KEY     | PRIMARY KEY (project_id, agent_id)
 ext          | gemini_cli_state   | gemini_cli_state_pkey                                           | PRIMARY KEY     | PRIMARY KEY (project_id, agent_id)
 ext          | hermes_state       | hermes_state_pkey                                               | PRIMARY KEY     | PRIMARY KEY (project_id, agent_id)
 ext          | openai_codex_state | openai_codex_state_pkey                                         | PRIMARY KEY     | PRIMARY KEY (project_id, agent_id)
 ext          | openclaw_state     | openclaw_state_pkey                                             | PRIMARY KEY     | PRIMARY KEY (project_id, agent_id)
 shared       | agent_leases       | agent_leases_agent_id_fkey                                      | FOREIGN KEY     | FOREIGN KEY (agent_id) REFERENCES core.agents(agent_id) ON DELETE CASCADE
 shared       | agent_leases       | agent_leases_project_id_fkey                                    | FOREIGN KEY     | FOREIGN KEY (project_id) REFERENCES core.projects(project_id) ON DELETE CASCADE
 shared       | agent_leases       | agent_leases_pkey                                               | PRIMARY KEY     | PRIMARY KEY (lease_id)
 shared       | agent_leases       | agent_leases_project_id_lease_scope_type_lease_scope_key_re_key | UNIQUE          | UNIQUE (project_id, lease_scope_type, lease_scope_key, released_at)
 shared       | artifacts          | artifacts_producer_agent_id_fkey                                | FOREIGN KEY     | FOREIGN KEY (producer_agent_id) REFERENCES core.agents(agent_id) ON DELETE SET NULL
 shared       | artifacts          | artifacts_project_id_fkey                                       | FOREIGN KEY     | FOREIGN KEY (project_id) REFERENCES core.projects(project_id) ON DELETE CASCADE
 shared       | artifacts          | artifacts_pkey                                                  | PRIMARY KEY     | PRIMARY KEY (artifact_id)
 shared       | core_state         | core_state_project_id_fkey                                      | FOREIGN KEY     | FOREIGN KEY (project_id) REFERENCES core.projects(project_id) ON DELETE CASCADE
 shared       | core_state         | core_state_source_agent_id_fkey                                 | FOREIGN KEY     | FOREIGN KEY (source_agent_id) REFERENCES core.agents(agent_id) ON DELETE SET NULL
 shared       | core_state         | core_state_source_event_id_fkey                                 | FOREIGN KEY     | FOREIGN KEY (source_event_id) REFERENCES shared.events(event_id) ON DELETE SET NULL
 shared       | core_state         | core_state_pkey                                                 | PRIMARY KEY     | PRIMARY KEY (state_id)
 shared       | core_state         | core_state_project_id_scope_type_scope_key_state_key_key        | UNIQUE          | UNIQUE (project_id, scope_type, scope_key, state_key)
 shared       | decisions          | decisions_made_by_agent_id_fkey                                 | FOREIGN KEY     | FOREIGN KEY (made_by_agent_id) REFERENCES core.agents(agent_id) ON DELETE SET NULL
 shared       | decisions          | decisions_project_id_fkey                                       | FOREIGN KEY     | FOREIGN KEY (project_id) REFERENCES core.projects(project_id) ON DELETE CASCADE
 shared       | decisions          | decisions_supersedes_decision_id_fkey                           | FOREIGN KEY     | FOREIGN KEY (supersedes_decision_id) REFERENCES shared.decisions(decision_id) ON DELETE SET NULL
 shared       | decisions          | decisions_pkey                                                  | PRIMARY KEY     | PRIMARY KEY (decision_id)
 shared       | decisions          | decisions_project_id_decision_key_key                           | UNIQUE          | UNIQUE (project_id, decision_key)
 shared       | events             | events_agent_id_fkey                                            | FOREIGN KEY     | FOREIGN KEY (agent_id) REFERENCES core.agents(agent_id) ON DELETE SET NULL
 shared       | events             | events_project_id_fkey                                          | FOREIGN KEY     | FOREIGN KEY (project_id) REFERENCES core.projects(project_id) ON DELETE CASCADE
 shared       | events             | events_pkey                                                     | PRIMARY KEY     | PRIMARY KEY (event_id)
 shared       | events             | events_project_id_idempotency_key_key                           | UNIQUE          | UNIQUE (project_id, idempotency_key)
 shared       | handoffs           | handoffs_status_check                                           | CHECK           | CHECK (status = ANY (ARRAY['open'::text, 'accepted'::text, 'rejected'::text, 'completed'::text]))
 shared       | handoffs           | handoffs_from_agent_id_fkey                                     | FOREIGN KEY     | FOREIGN KEY (from_agent_id) REFERENCES core.agents(agent_id) ON DELETE SET NULL
 shared       | handoffs           | handoffs_project_id_fkey                                        | FOREIGN KEY     | FOREIGN KEY (project_id) REFERENCES core.projects(project_id) ON DELETE CASCADE
 shared       | handoffs           | handoffs_to_agent_id_fkey                                       | FOREIGN KEY     | FOREIGN KEY (to_agent_id) REFERENCES core.agents(agent_id) ON DELETE SET NULL
 shared       | handoffs           | handoffs_pkey                                                   | PRIMARY KEY     | PRIMARY KEY (handoff_id)
 shared       | tasks              | tasks_priority_check                                            | CHECK           | CHECK (priority = ANY (ARRAY['low'::text, 'medium'::text, 'high'::text, 'critical'::text]))
 shared       | tasks              | tasks_status_check                                              | CHECK           | CHECK (status = ANY (ARRAY['todo'::text, 'in_progress'::text, 'blocked'::text, 'review'::text, 'done'::text, 'cancelled'::text]))
 shared       | tasks              | tasks_assigned_agent_id_fkey                                    | FOREIGN KEY     | FOREIGN KEY (assigned_agent_id) REFERENCES core.agents(agent_id) ON DELETE SET NULL
 shared       | tasks              | tasks_parent_task_id_fkey                                       | FOREIGN KEY     | FOREIGN KEY (parent_task_id) REFERENCES shared.tasks(task_id) ON DELETE SET NULL
 shared       | tasks              | tasks_project_id_fkey                                           | FOREIGN KEY     | FOREIGN KEY (project_id) REFERENCES core.projects(project_id) ON DELETE CASCADE
 shared       | tasks              | tasks_requested_by_agent_id_fkey                                | FOREIGN KEY     | FOREIGN KEY (requested_by_agent_id) REFERENCES core.agents(agent_id) ON DELETE SET NULL
 shared       | tasks              | tasks_pkey                                                      | PRIMARY KEY     | PRIMARY KEY (task_id)
 shared       | tasks              | tasks_project_id_canonical_title_key                            | UNIQUE          | UNIQUE (project_id, canonical_title)
(52 rows)

```

## Indexes
```text
 schemaname |     tablename      |                            indexname                            |                                                                                      indexdef                                                                                       
------------+--------------------+-----------------------------------------------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
 core       | agents             | agents_agent_key_key                                            | CREATE UNIQUE INDEX agents_agent_key_key ON core.agents USING btree (agent_key)
 core       | agents             | agents_pkey                                                     | CREATE UNIQUE INDEX agents_pkey ON core.agents USING btree (agent_id)
 core       | project_agents     | project_agents_pkey                                             | CREATE UNIQUE INDEX project_agents_pkey ON core.project_agents USING btree (project_id, agent_id)
 core       | projects           | projects_external_key_key                                       | CREATE UNIQUE INDEX projects_external_key_key ON core.projects USING btree (external_key)
 core       | projects           | projects_pkey                                                   | CREATE UNIQUE INDEX projects_pkey ON core.projects USING btree (project_id)
 ext        | agent_runtime_base | agent_runtime_base_pkey                                         | CREATE UNIQUE INDEX agent_runtime_base_pkey ON ext.agent_runtime_base USING btree (project_id, agent_id)
 ext        | agent_zero_state   | agent_zero_state_pkey                                           | CREATE UNIQUE INDEX agent_zero_state_pkey ON ext.agent_zero_state USING btree (project_id, agent_id)
 ext        | claude_code_state  | claude_code_state_pkey                                          | CREATE UNIQUE INDEX claude_code_state_pkey ON ext.claude_code_state USING btree (project_id, agent_id)
 ext        | gemini_cli_state   | gemini_cli_state_pkey                                           | CREATE UNIQUE INDEX gemini_cli_state_pkey ON ext.gemini_cli_state USING btree (project_id, agent_id)
 ext        | hermes_state       | hermes_state_pkey                                               | CREATE UNIQUE INDEX hermes_state_pkey ON ext.hermes_state USING btree (project_id, agent_id)
 ext        | openai_codex_state | openai_codex_state_pkey                                         | CREATE UNIQUE INDEX openai_codex_state_pkey ON ext.openai_codex_state USING btree (project_id, agent_id)
 ext        | openclaw_state     | openclaw_state_pkey                                             | CREATE UNIQUE INDEX openclaw_state_pkey ON ext.openclaw_state USING btree (project_id, agent_id)
 shared     | agent_leases       | agent_leases_pkey                                               | CREATE UNIQUE INDEX agent_leases_pkey ON shared.agent_leases USING btree (lease_id)
 shared     | agent_leases       | agent_leases_project_id_lease_scope_type_lease_scope_key_re_key | CREATE UNIQUE INDEX agent_leases_project_id_lease_scope_type_lease_scope_key_re_key ON shared.agent_leases USING btree (project_id, lease_scope_type, lease_scope_key, released_at)
 shared     | agent_leases       | idx_leases_active                                               | CREATE INDEX idx_leases_active ON shared.agent_leases USING btree (project_id, lease_scope_type, lease_scope_key, expires_at) WHERE (released_at IS NULL)
 shared     | artifacts          | artifacts_pkey                                                  | CREATE UNIQUE INDEX artifacts_pkey ON shared.artifacts USING btree (artifact_id)
 shared     | artifacts          | idx_artifacts_project_type                                      | CREATE INDEX idx_artifacts_project_type ON shared.artifacts USING btree (project_id, artifact_type, updated_at DESC)
 shared     | artifacts          | idx_artifacts_unique_key                                        | CREATE UNIQUE INDEX idx_artifacts_unique_key ON shared.artifacts USING btree (project_id, artifact_type, artifact_key, COALESCE(version_label, 'current'::text))
 shared     | core_state         | core_state_pkey                                                 | CREATE UNIQUE INDEX core_state_pkey ON shared.core_state USING btree (state_id)
 shared     | core_state         | core_state_project_id_scope_type_scope_key_state_key_key        | CREATE UNIQUE INDEX core_state_project_id_scope_type_scope_key_state_key_key ON shared.core_state USING btree (project_id, scope_type, scope_key, state_key)
 shared     | core_state         | idx_core_state_json_gin                                         | CREATE INDEX idx_core_state_json_gin ON shared.core_state USING gin (value_json jsonb_path_ops)
 shared     | core_state         | idx_core_state_lookup                                           | CREATE INDEX idx_core_state_lookup ON shared.core_state USING btree (project_id, scope_type, scope_key, state_key)
 shared     | decisions          | decisions_pkey                                                  | CREATE UNIQUE INDEX decisions_pkey ON shared.decisions USING btree (decision_id)
 shared     | decisions          | decisions_project_id_decision_key_key                           | CREATE UNIQUE INDEX decisions_project_id_decision_key_key ON shared.decisions USING btree (project_id, decision_key)
 shared     | events             | events_pkey                                                     | CREATE UNIQUE INDEX events_pkey ON shared.events USING btree (event_id)
 shared     | events             | events_project_id_idempotency_key_key                           | CREATE UNIQUE INDEX events_project_id_idempotency_key_key ON shared.events USING btree (project_id, idempotency_key)
 shared     | events             | idx_events_payload_gin                                          | CREATE INDEX idx_events_payload_gin ON shared.events USING gin (event_payload jsonb_path_ops)
 shared     | events             | idx_events_project_created                                      | CREATE INDEX idx_events_project_created ON shared.events USING btree (project_id, created_at DESC)
 shared     | handoffs           | handoffs_pkey                                                   | CREATE UNIQUE INDEX handoffs_pkey ON shared.handoffs USING btree (handoff_id)
 shared     | tasks              | idx_tasks_project_status                                        | CREATE INDEX idx_tasks_project_status ON shared.tasks USING btree (project_id, status, priority, updated_at DESC)
 shared     | tasks              | tasks_pkey                                                      | CREATE UNIQUE INDEX tasks_pkey ON shared.tasks USING btree (task_id)
 shared     | tasks              | tasks_project_id_canonical_title_key                            | CREATE UNIQUE INDEX tasks_project_id_canonical_title_key ON shared.tasks USING btree (project_id, canonical_title)
(32 rows)

```

## Views
```text
 schemaname |    viewname     |                                         definition                                          
------------+-----------------+---------------------------------------------------------------------------------------------
 api        | project_summary |  SELECT p.project_id,                                                                      +
            |                 |     p.project_name,                                                                        +
            |                 |     p.project_slug,                                                                        +
            |                 |     p.status,                                                                              +
            |                 |     p.default_branch,                                                                      +
            |                 |     p.repo_url,                                                                            +
            |                 |     count(DISTINCT pa.agent_id) AS agent_count,                                            +
            |                 |     count(DISTINCT t.task_id) FILTER (WHERE (t.status <> 'done'::text)) AS open_tasks,     +
            |                 |     count(DISTINCT t.task_id) FILTER (WHERE (t.status = 'done'::text)) AS done_tasks,      +
            |                 |     count(DISTINCT h.handoff_id) FILTER (WHERE (h.status = 'open'::text)) AS open_handoffs,+
            |                 |     count(DISTINCT d.decision_id) AS decision_count,                                       +
            |                 |     count(DISTINCT ar.artifact_id) AS artifact_count,                                      +
            |                 |     max(ev.created_at) AS last_event_at,                                                   +
            |                 |     p.created_at,                                                                          +
            |                 |     p.updated_at                                                                           +
            |                 |    FROM ((((((core.projects p                                                              +
            |                 |      LEFT JOIN core.project_agents pa ON ((pa.project_id = p.project_id)))                 +
            |                 |      LEFT JOIN shared.tasks t ON ((t.project_id = p.project_id)))                          +
            |                 |      LEFT JOIN shared.handoffs h ON ((h.project_id = p.project_id)))                       +
            |                 |      LEFT JOIN shared.decisions d ON ((d.project_id = p.project_id)))                      +
            |                 |      LEFT JOIN shared.artifacts ar ON ((ar.project_id = p.project_id)))                    +
            |                 |      LEFT JOIN shared.events ev ON ((ev.project_id = p.project_id)))                       +
            |                 |   GROUP BY p.project_id;
(1 row)

```

## Materialized Views
```text
 schemaname | matviewname | definition 
------------+-------------+------------
(0 rows)

```

## Sequences
```text
 sequence_schema | sequence_name | data_type | start_value | minimum_value | maximum_value | increment | cycle_option 
-----------------+---------------+-----------+-------------+---------------+---------------+-----------+--------------
(0 rows)

```

## Routines (Functions/Procedures)
```text
 routine_schema |        routine_name        | routine_type |                                                                                                                              arguments                                                                                                                               |   returns    
----------------+----------------------------+--------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+--------------
 api            | append_event               | FUNCTION     | p_project_id bigint, p_agent_id bigint, p_event_type text, p_scope_type text, p_scope_key text, p_idempotency_key text, p_event_payload jsonb                                                                                                                        | bigint
 api            | attach_agent_to_project    | FUNCTION     | p_project_id bigint, p_agent_id bigint, p_role_name text, p_can_write_shared boolean, p_priority_weight integer, p_membership_metadata jsonb                                                                                                                         | void
 api            | bump_row_version           | FUNCTION     |                                                                                                                                                                                                                                                                      | trigger
 api            | canonical_key              | FUNCTION     | input text                                                                                                                                                                                                                                                           | text
 api            | claim_lease                | FUNCTION     | p_project_id bigint, p_agent_id bigint, p_scope_type text, p_scope_key text, p_lease_reason text, p_ttl_seconds integer                                                                                                                                              | uuid
 api            | project_lock_key           | FUNCTION     | p_project_id bigint                                                                                                                                                                                                                                                  | bigint
 api            | register_agent             | FUNCTION     | p_agent_key text, p_agent_family text, p_display_name text, p_model_hint text, p_capabilities jsonb, p_config jsonb                                                                                                                                                  | bigint
 api            | register_project           | FUNCTION     | p_external_key text, p_project_name text, p_default_branch text, p_repo_url text, p_metadata jsonb                                                                                                                                                                   | bigint
 api            | release_lease              | FUNCTION     | p_project_id bigint, p_agent_id bigint, p_scope_type text, p_scope_key text, p_lease_token uuid                                                                                                                                                                      | void
 api            | set_timestamps             | FUNCTION     |                                                                                                                                                                                                                                                                      | trigger
 api            | upsert_agent_runtime_state | FUNCTION     | p_agent_key text, p_project_id bigint, p_workspace_root text, p_cwd text, p_active_branch text, p_active_task_key text, p_local_state jsonb, p_compact_memory jsonb, p_pending_actions jsonb, p_last_prompt_digest text, p_last_seen_event_id bigint                 | void
 api            | upsert_artifact            | FUNCTION     | p_project_id bigint, p_artifact_type text, p_artifact_key text, p_location_uri text, p_content_hash text, p_version_label text, p_producer_agent_id bigint, p_artifact_metadata jsonb                                                                                | bigint
 api            | upsert_core_state          | FUNCTION     | p_project_id bigint, p_agent_id bigint, p_scope_type text, p_scope_key text, p_state_key text, p_value_json jsonb, p_value_text text, p_source_event_id bigint, p_confidence numeric, p_effective_at timestamp with time zone, p_expires_at timestamp with time zone | bigint
 api            | upsert_decision            | FUNCTION     | p_project_id bigint, p_decision_key text, p_title text, p_summary text, p_rationale text, p_chosen_option jsonb, p_alternatives jsonb, p_made_by_agent_id bigint                                                                                                     | bigint
 api            | upsert_task                | FUNCTION     | p_project_id bigint, p_title text, p_description text, p_status text, p_priority text, p_assigned_agent_id bigint, p_requested_by_agent_id bigint, p_depends_on jsonb, p_acceptance_criteria jsonb, p_task_metadata jsonb                                            | bigint
 public         | armor                      | FUNCTION     | bytea, text[], text[]                                                                                                                                                                                                                                                | text
 public         | armor                      | FUNCTION     | bytea                                                                                                                                                                                                                                                                | text
 public         | crypt                      | FUNCTION     | text, text                                                                                                                                                                                                                                                           | text
 public         | dearmor                    | FUNCTION     | text                                                                                                                                                                                                                                                                 | bytea
 public         | decrypt                    | FUNCTION     | bytea, bytea, text                                                                                                                                                                                                                                                   | bytea
 public         | decrypt_iv                 | FUNCTION     | bytea, bytea, bytea, text                                                                                                                                                                                                                                            | bytea
 public         | digest                     | FUNCTION     | bytea, text                                                                                                                                                                                                                                                          | bytea
 public         | digest                     | FUNCTION     | text, text                                                                                                                                                                                                                                                           | bytea
 public         | encrypt                    | FUNCTION     | bytea, bytea, text                                                                                                                                                                                                                                                   | bytea
 public         | encrypt_iv                 | FUNCTION     | bytea, bytea, bytea, text                                                                                                                                                                                                                                            | bytea
 public         | gen_random_bytes           | FUNCTION     | integer                                                                                                                                                                                                                                                              | bytea
 public         | gen_random_uuid            | FUNCTION     |                                                                                                                                                                                                                                                                      | uuid
 public         | gen_salt                   | FUNCTION     | text, integer                                                                                                                                                                                                                                                        | text
 public         | gen_salt                   | FUNCTION     | text                                                                                                                                                                                                                                                                 | text
 public         | hmac                       | FUNCTION     | text, text, text                                                                                                                                                                                                                                                     | bytea
 public         | hmac                       | FUNCTION     | bytea, bytea, text                                                                                                                                                                                                                                                   | bytea
 public         | pgp_armor_headers          | FUNCTION     | text, OUT key text, OUT value text                                                                                                                                                                                                                                   | SETOF record
 public         | pgp_key_id                 | FUNCTION     | bytea                                                                                                                                                                                                                                                                | text
 public         | pgp_pub_decrypt            | FUNCTION     | bytea, bytea, text                                                                                                                                                                                                                                                   | text
 public         | pgp_pub_decrypt            | FUNCTION     | bytea, bytea, text, text                                                                                                                                                                                                                                             | text
 public         | pgp_pub_decrypt            | FUNCTION     | bytea, bytea                                                                                                                                                                                                                                                         | text
 public         | pgp_pub_decrypt_bytea      | FUNCTION     | bytea, bytea, text, text                                                                                                                                                                                                                                             | bytea
 public         | pgp_pub_decrypt_bytea      | FUNCTION     | bytea, bytea                                                                                                                                                                                                                                                         | bytea
 public         | pgp_pub_decrypt_bytea      | FUNCTION     | bytea, bytea, text                                                                                                                                                                                                                                                   | bytea
 public         | pgp_pub_encrypt            | FUNCTION     | text, bytea, text                                                                                                                                                                                                                                                    | bytea
 public         | pgp_pub_encrypt            | FUNCTION     | text, bytea                                                                                                                                                                                                                                                          | bytea
 public         | pgp_pub_encrypt_bytea      | FUNCTION     | bytea, bytea, text                                                                                                                                                                                                                                                   | bytea
 public         | pgp_pub_encrypt_bytea      | FUNCTION     | bytea, bytea                                                                                                                                                                                                                                                         | bytea
 public         | pgp_sym_decrypt            | FUNCTION     | bytea, text                                                                                                                                                                                                                                                          | text
 public         | pgp_sym_decrypt            | FUNCTION     | bytea, text, text                                                                                                                                                                                                                                                    | text
 public         | pgp_sym_decrypt_bytea      | FUNCTION     | bytea, text                                                                                                                                                                                                                                                          | bytea
 public         | pgp_sym_decrypt_bytea      | FUNCTION     | bytea, text, text                                                                                                                                                                                                                                                    | bytea
 public         | pgp_sym_encrypt            | FUNCTION     | text, text, text                                                                                                                                                                                                                                                     | bytea
 public         | pgp_sym_encrypt            | FUNCTION     | text, text                                                                                                                                                                                                                                                           | bytea
 public         | pgp_sym_encrypt_bytea      | FUNCTION     | bytea, text                                                                                                                                                                                                                                                          | bytea
 public         | pgp_sym_encrypt_bytea      | FUNCTION     | bytea, text, text                                                                                                                                                                                                                                                    | bytea
(51 rows)

```

## Triggers
```text
 trigger_schema |   table_name   |      trigger_name      | action_timing | event_manipulation |            action_statement             
----------------+----------------+------------------------+---------------+--------------------+-----------------------------------------
 core           | agents         | trg_agents_ts          | BEFORE        | UPDATE             | EXECUTE FUNCTION api.set_timestamps()
 core           | agents         | trg_agents_ts          | BEFORE        | INSERT             | EXECUTE FUNCTION api.set_timestamps()
 core           | agents         | trg_agents_ver         | BEFORE        | UPDATE             | EXECUTE FUNCTION api.bump_row_version()
 core           | project_agents | trg_project_agents_ts  | BEFORE        | UPDATE             | EXECUTE FUNCTION api.set_timestamps()
 core           | project_agents | trg_project_agents_ts  | BEFORE        | INSERT             | EXECUTE FUNCTION api.set_timestamps()
 core           | project_agents | trg_project_agents_ver | BEFORE        | UPDATE             | EXECUTE FUNCTION api.bump_row_version()
 core           | projects       | trg_projects_ts        | BEFORE        | UPDATE             | EXECUTE FUNCTION api.set_timestamps()
 core           | projects       | trg_projects_ts        | BEFORE        | INSERT             | EXECUTE FUNCTION api.set_timestamps()
 core           | projects       | trg_projects_ver       | BEFORE        | UPDATE             | EXECUTE FUNCTION api.bump_row_version()
 shared         | artifacts      | trg_artifacts_ts       | BEFORE        | UPDATE             | EXECUTE FUNCTION api.set_timestamps()
 shared         | artifacts      | trg_artifacts_ts       | BEFORE        | INSERT             | EXECUTE FUNCTION api.set_timestamps()
 shared         | artifacts      | trg_artifacts_ver      | BEFORE        | UPDATE             | EXECUTE FUNCTION api.bump_row_version()
 shared         | core_state     | trg_core_state_ts      | BEFORE        | INSERT             | EXECUTE FUNCTION api.set_timestamps()
 shared         | core_state     | trg_core_state_ts      | BEFORE        | UPDATE             | EXECUTE FUNCTION api.set_timestamps()
 shared         | core_state     | trg_core_state_ver     | BEFORE        | UPDATE             | EXECUTE FUNCTION api.bump_row_version()
 shared         | decisions      | trg_decisions_ts       | BEFORE        | UPDATE             | EXECUTE FUNCTION api.set_timestamps()
 shared         | decisions      | trg_decisions_ts       | BEFORE        | INSERT             | EXECUTE FUNCTION api.set_timestamps()
 shared         | decisions      | trg_decisions_ver      | BEFORE        | UPDATE             | EXECUTE FUNCTION api.bump_row_version()
 shared         | handoffs       | trg_handoffs_ts        | BEFORE        | INSERT             | EXECUTE FUNCTION api.set_timestamps()
 shared         | handoffs       | trg_handoffs_ts        | BEFORE        | UPDATE             | EXECUTE FUNCTION api.set_timestamps()
 shared         | tasks          | trg_tasks_ts           | BEFORE        | UPDATE             | EXECUTE FUNCTION api.set_timestamps()
 shared         | tasks          | trg_tasks_ts           | BEFORE        | INSERT             | EXECUTE FUNCTION api.set_timestamps()
 shared         | tasks          | trg_tasks_ver          | BEFORE        | UPDATE             | EXECUTE FUNCTION api.bump_row_version()
(23 rows)

```

## Enum Types
```text
 enum_schema | enum_type | enumsortorder | enumlabel 
-------------+-----------+---------------+-----------
(0 rows)

```

