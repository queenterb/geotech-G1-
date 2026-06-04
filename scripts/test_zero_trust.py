#!/usr/bin/env python3
"""Test harness for the zero-trust policy engine."""
from cis.zero_trust import PolicyEngine, enforce_decision


def run_case(session):
    engine = PolicyEngine()
    decision = engine.evaluate(session)
    print("Session:", session)
    print("Decision:", decision)
    enforce_decision(decision, session)
    print("---")


def main():
    run_case({"session_id": "s-low", "user_risk_score": 0.2, "device_compliance": True})
    run_case({"session_id": "s-med", "user_risk_score": 0.6, "device_compliance": True})
    run_case({"session_id": "s-high", "user_risk_score": 0.9, "device_compliance": False})


if __name__ == "__main__":
    main()
