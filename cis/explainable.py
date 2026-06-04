"""Explainable-AI prototype: feature importance and evidence bundling for alerts.

This is a lightweight, model-agnostic explainer that uses heuristics to score
feature importance and aggregates evidence from threat intel and event fields.
"""
from __future__ import annotations

from typing import Dict, Any, List
import math

from .threat_intel import global_store

# Simple baselines for z-score style importance (prototype)
BASELINE = {
    "modified_files_count": 5.0,
    "encryption_indicator": 0.05,
    "entropy": 3.0,
    "power_pkg_watts": 30.0,
}
BASE_STD = {
    "modified_files_count": 10.0,
    "encryption_indicator": 0.1,
    "entropy": 1.5,
    "power_pkg_watts": 10.0,
}


def _z_score(val: float, mean: float, std: float) -> float:
    if std <= 0:
        return 0.0
    return (val - mean) / std


def compute_feature_importance(event: Dict[str, Any]) -> List[Dict[str, Any]]:
    feats = []
    # numeric features we care about
    for k in ("modified_files_count", "encryption_indicator", "entropy", "power_pkg_watts"):
        v = event.get(k)
        if v is None:
            continue
        mean = BASELINE.get(k, 0.0)
        std = BASE_STD.get(k, 1.0)
        z = _z_score(float(v), mean, std)
        score = max(0.0, min(1.0, abs(z) / 3.0))  # normalize to [0,1]
        reason = f"value {v} vs baseline {mean} (z={z:.2f})"
        feats.append({"feature": k, "score": round(score, 3), "reason": reason})

    # sort by score desc
    feats = sorted(feats, key=lambda x: x["score"], reverse=True)
    return feats


def gather_evidence(event: Dict[str, Any]) -> List[Dict[str, Any]]:
    evidence = []
    # Threat intel matches
    try:
        store = global_store()
        matches = store.enrich_event(event)
        for m in matches:
            evidence.append({"type": "threat_intel", "indicator": m["indicator"], "matched_field": m["matched_field"]})
    except Exception:
        pass

    # Basic event fields
    if event.get("pid"):
        evidence.append({"type": "process", "pid": event.get("pid")})
    if event.get("filename"):
        evidence.append({"type": "file", "filename": event.get("filename")})

    return evidence


def explain_alert_event(event: Dict[str, Any]) -> Dict[str, Any]:
    fi = compute_feature_importance(event)
    ev = gather_evidence(event)
    # derive a simple confidence score
    conf = 0.0
    if fi:
        conf = max(f.get("score", 0.0) for f in fi)
    if ev:
        conf = min(1.0, conf + 0.2)
    return {"feature_importance": fi, "evidence": ev, "confidence": round(conf, 3)}
