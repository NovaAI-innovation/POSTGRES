from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import tempfile
from pathlib import Path


def _read_stdin_json() -> dict:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _event_type_for(hook_event_name: str) -> str:
    if hook_event_name in {"PostToolUse", "Stop"}:
        return "task_outcome"
    if hook_event_name in {"SessionStart", "PermissionRequest"}:
        return "fact"
    if hook_event_name == "UserPromptSubmit":
        return "preference"
    return "message"


def _append_local_log(log_path: Path, payload: dict) -> None:
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=True, separators=(",", ":")) + "\n")
        return
    except Exception:  # noqa: BLE001
        pass

    # Fail-open fallback when repo-local log path is not writable.
    fallback = Path(tempfile.gettempdir()) / "codex_gateway_hook_events.jsonl"
    try:
        with fallback.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=True, separators=(",", ":")) + "\n")
    except Exception:  # noqa: BLE001
        # Hooks should never fail hard on telemetry logging issues.
        pass


def main() -> int:
    if os.getenv("CODEX_GATEWAY_HOOKS_ENABLED", "true").lower() == "false":
        if os.getenv("CODEX_HOOK_EVENT_NAME") == "Stop":
            print(json.dumps({"continue": True}))
        return 0

    hook = _read_stdin_json()
    hook_event_name = str(hook.get("hook_event_name", "Unknown"))

    repo_root = Path(hook.get("cwd") or os.getcwd())
    gateway_script = repo_root / ".codex" / "scripts" / "codex_gateway.sh"
    if not gateway_script.exists():
        if hook_event_name == "Stop":
            print(json.dumps({"continue": True}))
        return 0

    session_id = str(hook.get("session_id", ""))
    turn_id = str(hook.get("turn_id", ""))
    model = str(hook.get("model", ""))
    source = str(hook.get("source", ""))
    tool_name = str(hook.get("tool_name", ""))
    prompt = str(hook.get("prompt", ""))
    last_assistant_message = str(hook.get("last_assistant_message", ""))
    tool_input = hook.get("tool_input")
    tool_response = hook.get("tool_response")

    details = {
        "hook_event_name": hook_event_name,
        "session_id": session_id,
        "turn_id": turn_id,
        "cwd": str(repo_root),
        "model": model,
        "source": source,
        "tool_name": tool_name,
        "prompt": prompt[:1500],
        "last_assistant_message": last_assistant_message[:1500],
        "tool_input": tool_input,
        "tool_response": tool_response,
        "timestamp": int(time.time()),
    }
    compact_details = json.dumps(details, ensure_ascii=True, separators=(",", ":"))

    project_scope = os.getenv("CODEX_PROJECT_SCOPE_GROUP_ID", "project-codex")
    event_payload = {
        "event_type": _event_type_for(hook_event_name),
        "content": f"codex_hook_event {compact_details[:5000]}",
        "confidence": float(os.getenv("CODEX_HOOK_EVENT_CONFIDENCE", "0.95")),
        "scope": os.getenv("CODEX_HOOK_EVENT_SCOPE", "scoped"),
        "group_id": project_scope,
        "source_ref": f"hook:{hook_event_name}:{session_id}:{turn_id or 'na'}",
    }

    cmd = [
        "bash",
        str(gateway_script),
        "--mode",
        os.getenv("CODEX_HOOK_GATEWAY_MODE", "remote"),
        "--operation",
        "memory_event",
        "--event-json",
        json.dumps(event_payload, ensure_ascii=True),
        "--project-scope-id",
        project_scope,
    ]
    gateway_url = os.getenv("CODEX_HOOK_GATEWAY_URL", "").strip()
    if gateway_url:
        cmd.extend(["--gateway-url", gateway_url])

    rc = 0
    out = ""
    err = ""
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=int(os.getenv("CODEX_HOOK_GATEWAY_TIMEOUT_SECONDS", "20")),
            check=False,
        )
        rc = int(completed.returncode)
        out = completed.stdout[-4000:]
        err = completed.stderr[-4000:]
    except Exception as exc:  # noqa: BLE001
        rc = 1
        err = str(exc)

    log_path = Path(os.getenv("CODEX_HOOK_LOG_PATH", str(repo_root / ".codex" / "runtime" / "hook_events.jsonl")))
    _append_local_log(
        log_path,
        {
            "hook": details,
            "gateway_cmd": cmd,
            "gateway_rc": rc,
            "gateway_stdout_tail": out,
            "gateway_stderr_tail": err,
        },
    )

    # Stop hooks must emit JSON when exiting 0.
    if hook_event_name == "Stop":
        print(json.dumps({"continue": True}))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
