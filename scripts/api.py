from __future__ import annotations

import os
import json
import subprocess
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), "..", "dashboard"))

# Default alerts file (matches cis/main_detector CONFIG)
ALERTS_FILE = os.environ.get("CIS_ALERTS_FILE") or os.path.join(os.path.dirname(os.path.dirname(__file__)), "tmp", "cis_alerts.jsonl")
PLAYBOOKS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "playbooks")
PLAYBOOK_RUNNER = os.path.join(os.path.dirname(__file__), "playbook_runner.py")


def load_alerts(n: int = 100):
    out = []
    try:
        with open(ALERTS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    out.append(json.loads(line))
                except Exception:
                    continue
    except Exception:
        pass
    return out[-n:]


@app.route("/alerts")
def alerts():
    n = int(request.args.get("n", 50))
    return jsonify(load_alerts(n))


@app.route("/explain", methods=["POST"])
def explain():
    payload = request.json or {}
    try:
        from cis.alert_explanation import explain_alert
        res = explain_alert(payload)
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/playbooks")
def list_playbooks():
    out = []
    try:
        for f in os.listdir(PLAYBOOKS_DIR):
            if f.endswith(".yaml") or f.endswith(".yml"):
                out.append(f)
    except Exception:
        pass
    return jsonify(out)


@app.route("/run_playbook", methods=["POST"])
def run_playbook():
    data = request.json or {}
    pb = data.get("playbook")
    pid = data.get("pid")
    apply_flag = data.get("apply", False)
    if not pb:
        return jsonify({"error": "missing playbook"}), 400
    pb_path = os.path.join(PLAYBOOKS_DIR, pb)
    if not os.path.exists(pb_path):
        return jsonify({"error": "playbook not found"}), 404
    cmd = ["python", PLAYBOOK_RUNNER, pb_path]
    if pid:
        cmd += ["--pid", str(pid)]
    if apply_flag:
        cmd += ["--apply"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return jsonify({"returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/")
def ui_index():
    return send_from_directory(app.static_folder, "index.html")


if __name__ == "__main__":
    # ensure alerts dir exists
    os.makedirs(os.path.dirname(ALERTS_FILE), exist_ok=True)
    app.run(host="127.0.0.1", port=8000, debug=True)
