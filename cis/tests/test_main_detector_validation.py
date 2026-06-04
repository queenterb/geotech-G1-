import unittest

from main_detector import validate_event_payload


class TestMainDetectorValidation(unittest.TestCase):
    def test_valid_event(self):
        ev = validate_event_payload(
            {
                "pid": 123,
                "uid": 1000,
                "timestamp": 1000.0,
                "comm": "proc",
                "filename": "/tmp/a",
                "op_type": 2,
            }
        )
        self.assertIsNotNone(ev)
        self.assertEqual(ev.pid, 123)

    def test_invalid_missing_field(self):
        ev = validate_event_payload({"pid": 1, "op_type": 2})
        self.assertIsNone(ev)

    def test_invalid_op_type(self):
        ev = validate_event_payload(
            {
                "pid": 1,
                "timestamp": 1000.0,
                "filename": "/tmp/a",
                "op_type": 999,
            }
        )
        self.assertIsNone(ev)


if __name__ == "__main__":
    unittest.main()
