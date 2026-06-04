import json
import sys
from collections import Counter
from datetime import datetime

try:
    from .alert_explanation import annotate_alert
except ImportError:
    from alert_explanation import annotate_alert

ALERTS_FILE = sys.argv[1] if len(sys.argv) > 1 else "../cis_alerts.jsonl"

alerts = []
try:
    with open(ALERTS_FILE, "r") as f:
        for line in f:
            if line.strip():
                alerts.append(json.loads(line))
except Exception as e:
    print(f"Failed to read alerts: {e}")
    sys.exit(1)

if not alerts:
    print("No alerts found.")
    sys.exit(0)

alerts = [annotate_alert(a) for a in alerts]

# Count by event type
by_event = Counter(a.get("event", "unknown") for a in alerts)
# Count by PID
by_pid = Counter(a.get("pid", "unknown") for a in alerts)
# Alerts per day
by_day = Counter(datetime.fromtimestamp(a.get("timestamp", 0)).strftime("%Y-%m-%d") for a in alerts)

print("Alert Summary:")
print(f"Total alerts: {len(alerts)}")
print(f"By event type: {dict(by_event)}")
print(f"By PID: {dict(by_pid)}")
print(f"Alerts per day: {dict(by_day)}")

# Show last 5 alerts

def fmt_alert(a):
    summary = a.get("explanation", {}).get("summary", "No explanation")
    recommendation = a.get("explanation", {}).get("recommended_action", "No recommendation")
    return (
        f"[{datetime.fromtimestamp(a['timestamp'])}] PID {a['pid']} - {a['event']} - "
        f"Summary: {summary} - Recommendation: {recommendation}"
    )

print("\nLast 5 alerts:")
for a in alerts[-5:]:
    print(fmt_alert(a))
