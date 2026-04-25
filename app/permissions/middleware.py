from __future__ import annotations

from app.permissions.policy_engine import PolicyDecision


class PolicyError(Exception):
    pass


def require_allowed(decision: PolicyDecision) -> None:
    if not decision.allowed:
        raise PolicyError(decision.reason)
