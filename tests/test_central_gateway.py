from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATEWAY_PATH = ROOT / "scripts" / "gateway" / "central_gateway.py"
POLICY_DIR = ROOT / "scripts" / "gateway" / "policies"

_SPEC = importlib.util.spec_from_file_location("central_gateway", GATEWAY_PATH)
assert _SPEC and _SPEC.loader
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules["central_gateway"] = _MODULE
_SPEC.loader.exec_module(_MODULE)

classify_event = _MODULE.classify_event
path_allowed = _MODULE.path_allowed
should_persist_event = _MODULE.should_persist_event


def _load(name: str) -> dict:
    return json.loads((POLICY_DIR / name).read_text(encoding="utf-8"))


def test_classify_event_prefers_explicit_type() -> None:
    policy = _load("claude.json")
    event = {"event_type": "task_outcome", "content": "unrelated text"}
    assert classify_event(policy, event) == "task_outcome"


def test_should_persist_blocks_sensitive() -> None:
    policy = _load("claude.json")
    event = {"content": "password=abc", "confidence": 0.99}
    persist, reason, _, sensitive = should_persist_event(policy, event)
    assert persist is False
    assert reason == "sensitive_blocked"
    assert sensitive is True


def test_should_persist_blocks_shared_when_not_allowed() -> None:
    policy = _load("agent-a.json")
    event = {
        "event_type": "task_outcome",
        "content": "migration completed",
        "confidence": 0.99,
        "scope": "shared",
    }
    persist, reason, _, _ = should_persist_event(policy, event)
    assert persist is False
    assert reason == "shared_scope_blocked"


def test_path_allowlist_enforced() -> None:
    profiles = _load("agent_profiles.json")["agents"]
    claude = profiles["Claude"]
    assert path_allowed(claude, "POST", "/tasks") is True
    assert path_allowed(claude, "POST", "/admin/pause-agents") is False
    assert path_allowed(claude, "DELETE", "/tasks") is False
