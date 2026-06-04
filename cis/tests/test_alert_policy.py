import json
import tempfile
import os
import pytest
from ..main_detector import CISMain

class DummyIntervention:
    def intervene(self, pid, rollback_needed=False):
        class Result:
            isolated = True
            snapshot = "snap"
            rolled_back = rollback_needed
        return Result()

def test_policy_override(monkeypatch):
    # Setup dummy config with policy
    config = {
        "divergence_threshold": 0.5,
        "encryption_threshold": 0.5,
        "heuristic_write_threshold": 100,
        "policy": {
            "divergence_threshold": 0.1,
            "encryption_threshold": 0.2,
            "heuristic_write_threshold": 10,
            "auto_isolate": True,
            "auto_rollback": True
        },
        "alerts_file": tempfile.mktemp(),
        "status_file": tempfile.mktemp(),
        "heartbeat_file": tempfile.mktemp(),
        "model_path": "",
        "immune_memory_path": tempfile.mktemp(),
        "ebpf_socket_path": tempfile.mktemp(),
        "log_file": tempfile.mktemp(),
        "log_max_bytes": 100000,
        "log_backup_count": 1
    }
    main = CISMain(config)
    main.intervention = DummyIntervention()
    # Simulate state
    main.fs_state.encryption_indicator = 0.3
    # Should use policy override
    assert main.policy["divergence_threshold"] == 0.1
    assert main.policy["encryption_threshold"] == 0.2
    assert main.policy["auto_isolate"] is True
    assert main.policy["auto_rollback"] is True

# To run: pytest tests/test_alert_policy.py
