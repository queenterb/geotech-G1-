import json
import os
import tempfile
import unittest

from cis.dashboard_new import app


class HttpEndpointsTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.tmpdir = tempfile.TemporaryDirectory()
        self.status_file = os.path.join(self.tmpdir.name, "cis_status.json")
        self.telemetry_file = os.path.join(self.tmpdir.name, "cis_live_events.jsonl")
        os.environ["CIS_STATUS_PATH"] = self.status_file
        os.environ["CIS_TELEMETRY_STORAGE_PATH"] = self.telemetry_file

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_healthz_endpoint(self):
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "ok")

    def test_status_endpoint_returns_json(self):
        response = self.client.get("/api/status")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("status", data)

    def test_telemetry_ingest_endpoint_accepts_valid_payload(self):
        payload = {
            "pid": 333,
            "timestamp": 1710000000.123,
            "filename": "deploy.bin",
            "op_type": 2,
            "uid": 0,
            "comm": "deploy"
        }
        response = self.client.post("/api/telemetry", json=payload)
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertTrue(data["accepted"])
        self.assertTrue(os.path.exists(self.telemetry_file))

    def test_telemetry_ingest_endpoint_rejects_invalid_payload(self):
        response = self.client.post("/api/telemetry", json={"pid": 1})
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("error", data)


if __name__ == "__main__":
    unittest.main()
