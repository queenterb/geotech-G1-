import os
import tempfile
import unittest

from cis.telemetry_ingest import TelemetryIngestionService


class TelemetryIngestTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.storage_path = os.path.join(self.tmpdir.name, "telemetry.jsonl")
        self.service = TelemetryIngestionService(storage_path=self.storage_path)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_ingest_accepts_live_payload(self):
        payload = {
            "pid": 777,
            "timestamp": 1710000000.123,
            "filename": "important.bin",
            "op_type": 2,
            "uid": 1000,
            "comm": "encryptor"
        }
        result = self.service.ingest_payload(payload)

        self.assertTrue(result["accepted"])
        self.assertEqual(result["pid"], 777)
        self.assertTrue(os.path.exists(self.storage_path))

    def test_ingest_rejects_invalid_payload(self):
        with self.assertRaises(ValueError):
            self.service.ingest_payload({"pid": 2, "filename": "bad"})


if __name__ == "__main__":
    unittest.main()
