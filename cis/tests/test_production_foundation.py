import os
import tempfile
import unittest
from unittest.mock import patch

from cis import database
from cis import auth


class ProductionFoundationTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, "cis_test.db")
        self.env = patch.dict(os.environ, {"CIS_DB_PATH": self.db_path}, clear=False)
        self.env.start()
        database.init_database()

    def tearDown(self):
        self.env.stop()
        self.tmpdir.cleanup()

    def test_init_database_creates_required_tables(self):
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('users','subscriptions','sessions','audit_events')")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()

        self.assertTrue({"users", "subscriptions", "sessions", "audit_events"}.issubset(tables))

    def test_sessions_are_persisted_and_validated(self):
        token_data = auth.create_session_token(42, 7, expires_in_hours=1)
        self.assertTrue(token_data["token"])

        validated = auth.validate_session_token(token_data["token"])
        self.assertTrue(validated["valid"])
        self.assertEqual(validated["user_id"], 42)

        invalidated = auth.invalidate_session_token(token_data["token"])
        self.assertTrue(invalidated)

        self.assertIsNone(auth.validate_session_token(token_data["token"]))


if __name__ == "__main__":
    unittest.main()
