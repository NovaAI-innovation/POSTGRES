from __future__ import annotations

import json
import re
from pathlib import Path


POLICY_DIR = Path(__file__).resolve().parents[1] / "scripts" / "gateway" / "policies"
EVENT_POLICY_FILES = ("claude.json", "agent-a.json", "agent-b.json")


def load_policy(name: str) -> dict:
    return json.loads((POLICY_DIR / name).read_text(encoding="utf-8"))


def detect_event_class(policy: dict, event: dict) -> str:
    event_type = event.get("event_type")
    rules = policy["rules"]
    if event_type and event_type in rules:
        return event_type

    content = event.get("content", "")
    for rule_name, rule in rules.items():
        for pattern in rule.get("detect_patterns", []):
            if re.search(pattern, content):
                return rule_name
    return policy["default_rule"]


def should_persist(policy: dict, event: dict) -> bool:
    event_class = detect_event_class(policy, event)
    rule = policy["rules"][event_class]
    if not rule["enabled"]:
        return False

    confidence = float(event.get("confidence", 1.0))
    if confidence < float(rule["min_confidence"]):
        return False

    content = event.get("content", "")
    sensitive = any(re.search(pattern, content) for pattern in policy["sensitive_patterns"])
    if sensitive and not policy["sensitive_handling"]["persist_sensitive"]:
        return False

    if event.get("scope") == "shared" and not policy["allow_shared_scope"]:
        return False

    return True


def test_policy_files_have_required_structure() -> None:
    required_top_level = {
        "policy_name",
        "policy_version",
        "default_scope",
        "default_rule",
        "allow_shared_scope",
        "sensitive_patterns",
        "sensitive_handling",
        "rules",
    }
    for file_name in EVENT_POLICY_FILES:
        path = POLICY_DIR / file_name
        policy = json.loads(path.read_text(encoding="utf-8"))
        assert required_top_level.issubset(policy.keys())
        assert policy["default_rule"] in policy["rules"]
        for _, rule in policy["rules"].items():
            assert {"enabled", "min_confidence", "tags", "detect_patterns"}.issubset(rule.keys())


def test_agent_profiles_intentionally_differ() -> None:
    claude = load_policy("claude.json")
    agent_a = load_policy("agent-a.json")
    agent_b = load_policy("agent-b.json")

    assert float(claude["rules"]["preference"]["min_confidence"]) > float(agent_b["rules"]["preference"]["min_confidence"])
    assert agent_a["allow_shared_scope"] is False
    assert agent_b["allow_shared_scope"] is True


def test_shared_scope_blocked_for_claude_but_allowed_for_agent_b() -> None:
    shared_event = {
        "event_type": "task_outcome",
        "content": "Task completed successfully.",
        "confidence": 0.95,
        "scope": "shared",
    }
    assert should_persist(load_policy("claude.json"), shared_event) is False
    assert should_persist(load_policy("agent-b.json"), shared_event) is True


def test_sensitive_content_is_blocked_from_persistence() -> None:
    event = {
        "content": "password=abc123 should never be persisted",
        "confidence": 0.99,
    }
    assert should_persist(load_policy("claude.json"), event) is False
    assert should_persist(load_policy("agent-a.json"), event) is False
    assert should_persist(load_policy("agent-b.json"), event) is False


def test_low_confidence_message_is_skipped() -> None:
    event = {"content": "just a casual chat message", "confidence": 0.4}
    assert should_persist(load_policy("claude.json"), event) is False
    assert should_persist(load_policy("agent-a.json"), event) is False
    assert should_persist(load_policy("agent-b.json"), event) is False
