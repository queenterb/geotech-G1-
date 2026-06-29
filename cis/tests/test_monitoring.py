import json
import os
import tempfile
import unittest

from cis.monitoring import OperationalMonitor


class MonitoringTests(unittest.TestCase):
    def test_monitor_writes_status_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "status.json")
            monitor = OperationalMonitor(status_path=path)
            payload = monitor.write_status({"uptime_seconds": 12, "alerts": 1})
            self.assertEqual(payload["status"], "running")
            self.assertTrue(os.path.exists(path))
            with open(path, "r", encoding="utf-8") as handle:
                stored = json.load(handle)
            self.assertEqual(stored["uptime_seconds"], 12)


if __name__ == "__main__":
    unittest.main()
