"""Simple threat-intel ingestion and enrichment prototype.

This module ingests basic STIX JSON (or simplified indicator lists) and
provides a lightweight enrichment API for events.
"""
from __future__ import annotations

import json
import os
import re
from typing import List, Dict, Any

STORE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "intel_store.json")


class ThreatIntelStore:
    def __init__(self, path: str = STORE_PATH):
        self.path = path
        self.indicators: List[Dict[str, Any]] = []
        self._load()

    def _load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                self.indicators = json.load(f)
        except Exception:
            self.indicators = []

    def _save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.indicators, f, indent=2)

    def ingest_stix(self, stix_path: str) -> int:
        """Ingest a STIX JSON file (prototype). Returns number of indicators added."""
        added = 0
        try:
            with open(stix_path, "r", encoding="utf-8") as f:
                doc = json.load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to load STIX file: {e}")

        objs = doc.get("objects") or doc.get("indicators") or []
        for o in objs:
            if isinstance(o, dict) and o.get("type") == "indicator":
                pattern = o.get("pattern") or o.get("value") or ""
                if not pattern:
                    continue
                # Extract simple values from patterns like [file:path = '/tmp/x'] or [ipv4-addr:value = '1.2.3.4']
                m_ip = re.search(r"'?(\d+\.\d+\.\d+\.\d+)'?", pattern)
                m_file = re.search(r"'?(\/[^']+)'?", pattern)
                m_domain = re.search(r"'?(?:\w+\.)+\w+'?", pattern)
                indicator = {"raw_pattern": pattern, "type": "unknown", "value": pattern}
                if m_ip:
                    indicator["type"] = "ipv4"
                    indicator["value"] = m_ip.group(1)
                elif m_file:
                    indicator["type"] = "file"
                    indicator["value"] = m_file.group(1)
                elif m_domain:
                    indicator["type"] = "domain"
                    indicator["value"] = m_domain.group(0)
                else:
                    # fallback store raw pattern
                    indicator["type"] = "pattern"
                    indicator["value"] = pattern

                # avoid duplicates
                if not any(i.get("raw_pattern") == indicator["raw_pattern"] for i in self.indicators):
                    self.indicators.append(indicator)
                    added += 1

        if added:
            self._save()
        return added

    def list_indicators(self) -> List[Dict[str, Any]]:
        return list(self.indicators)

    def enrich_event(self, event: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Return matching indicators for the given event (simple heuristics)."""
        matches: List[Dict[str, Any]] = []
        filename = str(event.get("filename", "")).lower()
        src_ip = str(event.get("src_ip", ""))
        for ind in self.indicators:
            t = ind.get("type")
            v = str(ind.get("value", "")).lower()
            if t == "file" and v and v in filename:
                matches.append({"indicator": ind, "matched_field": "filename"})
            elif t == "ipv4" and v and v == src_ip:
                matches.append({"indicator": ind, "matched_field": "src_ip"})
            elif t == "domain" and v and v in str(event.get("hostname", "")).lower():
                matches.append({"indicator": ind, "matched_field": "hostname"})
            elif t == "pattern" and v and v in json.dumps(event).lower():
                matches.append({"indicator": ind, "matched_field": "payload"})
        return matches


_GLOBAL_STORE: ThreatIntelStore | None = None


def global_store() -> ThreatIntelStore:
    global _GLOBAL_STORE
    if _GLOBAL_STORE is None:
        _GLOBAL_STORE = ThreatIntelStore()
    return _GLOBAL_STORE


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("stix_file")
    args = parser.parse_args()
    s = ThreatIntelStore()
    added = s.ingest_stix(args.stix_file)
    print(f"Added {added} indicators")
