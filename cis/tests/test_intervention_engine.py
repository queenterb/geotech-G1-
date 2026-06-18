import unittest

from cis.intervention_engine import InterventionEngine


class TestInterventionEngine(unittest.TestCase):
    def test_intervene_with_invalid_pid(self):
        e = InterventionEngine()
        result = e.intervene(999999, rollback_needed=False)
        self.assertFalse(result.isolated)
        self.assertFalse(result.rolled_back)

    def test_snapshot_id_set(self):
        e = InterventionEngine()
        sid = e.take_snapshot()
        self.assertIsNotNone(sid)
        self.assertEqual(e.last_snapshot_id, sid)


if __name__ == "__main__":
    unittest.main()
