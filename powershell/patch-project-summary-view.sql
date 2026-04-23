-- Patch: add api.project_summary view referenced by agent-state.ps1 summary command
CREATE OR REPLACE VIEW api.project_summary AS
SELECT
  p.project_id,
  p.project_name,
  p.project_slug,
  p.status,
  p.default_branch,
  p.repo_url,
  COUNT(DISTINCT pa.agent_id)                                              AS agent_count,
  COUNT(DISTINCT t.task_id) FILTER (WHERE t.status <> 'done')             AS open_tasks,
  COUNT(DISTINCT t.task_id) FILTER (WHERE t.status = 'done')              AS done_tasks,
  COUNT(DISTINCT h.handoff_id) FILTER (WHERE h.status = 'open')           AS open_handoffs,
  COUNT(DISTINCT d.decision_id)                                            AS decision_count,
  COUNT(DISTINCT ar.artifact_id)                                           AS artifact_count,
  MAX(ev.created_at)                                                       AS last_event_at,
  p.created_at,
  p.updated_at
FROM core.projects p
LEFT JOIN core.project_agents pa  ON pa.project_id = p.project_id
LEFT JOIN shared.tasks t          ON t.project_id  = p.project_id
LEFT JOIN shared.handoffs h       ON h.project_id  = p.project_id
LEFT JOIN shared.decisions d      ON d.project_id  = p.project_id
LEFT JOIN shared.artifacts ar     ON ar.project_id = p.project_id
LEFT JOIN shared.events ev        ON ev.project_id = p.project_id
GROUP BY p.project_id;
