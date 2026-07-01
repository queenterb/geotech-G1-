import json
import tempfile
import unittest
from pathlib import Path

from cis.main_detector import validate_event_payload, SoftwareEvent


class LiveIngestTests(unittest.TestCase):
    def test_validate_event_payload_accepts_live_shape(self):
        payload = {
            "pid": 321,
            "timestamp": 1710000000.123,
            "filename": "invoice.docx",
            "op_type": 2,
            "uid": 1000,
            "comm": "rclone"
        }
        event = validate_event_payload(payload)
        self.assertIsNotNone(event)
        self.assertEqual(event.pid, 321)
        self.assertEqual(event.op_type, 2)

    def test_validate_event_payload_rejects_invalid_shape(self):
        payload = {"pid": 321, "filename": "invoice.docx"}
        self.assertIsNone(validate_event_payload(payload))


if __name__ == "__main__":
    unittest.main()
