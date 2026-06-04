"""Zero-Trust policy engine prototype.

Loads simple YAML policies and evaluates session/device/user attributes
to return a decision: `allow`, `challenge`, or `deny`.
"""
from __future__ import annotations

import yaml
import os
from typing import Any, Dict, List

POLICY_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "policies", "zero_trust_policy.yaml")


def _match_condition(value: Any, cond: Dict[str, Any]) -> bool:
    op = cond.get("op")
    target = cond.get("value")
    if op == "gt":
        return float(value) > float(target)
    if op == "lt":
        return float(value) < float(target)
    if op == "eq":
        return str(value) == str(target)
    if op == "in":
        return str(value) in str(target)
    if op == "contains":
        return str(target) in str(value)
    return False


class PolicyEngine:
    def __init__(self, path: str | None = None):
        self.path = path or POLICY_PATH
        self.policies = []
        self.load_policies()

    def load_policies(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                doc = yaml.safe_load(f)
        except Exception:
            doc = {}
        self.policies = doc.get("policies", []) or []

    def evaluate(self, session: Dict[str, Any]) -> Dict[str, Any]:
        # Evaluate policies in priority order; return first matching decision
        for p in sorted(self.policies, key=lambda x: x.get("priority", 100)):
            conds = p.get("conditions", [])
            if not conds:
                continue
            all_ok = True
            for c in conds:
                field = c.get("field")
                if field not in session:
                    all_ok = False
                    break
                if not _match_condition(session.get(field), c):
                    all_ok = False
                    break
            if all_ok:
                return {"policy_id": p.get("id"), "decision": p.get("decision"), "reason": p.get("description")}
        # default allow
        return {"policy_id": None, "decision": "allow", "reason": "default allow"}


def enforce_decision(decision: Dict[str, Any], session: Dict[str, Any]):
    # Enforcement adapters would call IAM, proxy, or endpoint management systems.
    # Prototype: print/log actions.
    dec = decision.get("decision")
    if dec == "deny":
        print(f"ENFORCE: deny session {session.get('session_id')} reason={decision.get('reason')}")
    elif dec == "challenge":
        print(f"ENFORCE: challenge (MFA) for session {session.get('session_id')} reason={decision.get('reason')}")
    else:
        print(f"ENFORCE: allow session {session.get('session_id')} (policy={decision.get('policy_id')})")


if __name__ == "__main__":
    import json
    e = PolicyEngine()
    sample = {"session_id": "s1", "user_risk_score": 0.6, "device_compliance": False}
    d = e.evaluate(sample)
    print(json.dumps(d, indent=2))
    enforce_decision(d, sample)
