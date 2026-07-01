import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cis import database
from cis import auth
from cis import service


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

    def test_build_service_config_prefers_live_config_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "cis"
            config_dir.mkdir(parents=True, exist_ok=True)
            (config_dir / "config.json").write_text(json.dumps({"smtp_server": "live.smtp.example"}), encoding="utf-8")
            (config_dir / "config.example.json").write_text(json.dumps({"smtp_server": "example.smtp.example"}), encoding="utf-8")

            old_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                with patch.dict(os.environ, {}, clear=False):
                    config = service.build_service_config()
            finally:
                os.chdir(old_cwd)

            self.assertEqual(config["smtp_server"], "live.smtp.example")

    def test_init_database_adds_missing_session_columns(self):
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS sessions")
        cursor.execute("""
            CREATE TABLE sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                subscription_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                revoked_at TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)
        conn.commit()
        conn.close()

        database.init_database()
        token_data = auth.create_session_token(42, 7, expires_in_hours=1)

        self.assertTrue(token_data["token"])


if __name__ == "__main__":
    unittest.main()
