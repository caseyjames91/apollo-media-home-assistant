import ast
import sqlite3
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SERVICE = (ROOT / "service.py").read_text(encoding="utf-8")
PROGRESS = (ROOT / "resources/lib/progress.py").read_text(encoding="utf-8")
PLAYBACK = (ROOT / "resources/lib/playback_session.py").read_text(encoding="utf-8")
SOURCE = (ROOT / "resources/lib/source_session.py").read_text(encoding="utf-8")
AMS = (ROOT / "resources/lib/ams.py").read_text(encoding="utf-8")


class ServiceAmsAuthorityTests(unittest.TestCase):
    def test_playback_monitor_has_no_direct_jellyfin_dependency(self):
        lowered = SERVICE.lower()
        self.assertNotIn("jellyfinclient", lowered)
        self.assertNotIn("jellyfin()", lowered)
        self.assertNotIn("report_playback", lowered)
        self.assertNotIn("set_resume", lowered)
        self.assertNotIn('getuniqueid("jellyfin")', lowered)
        self.assertNotIn("remote_jellyfin_item_id", lowered)
        self.assertNotIn("jellyfin_item_id", lowered)

    def test_session_contracts_are_provider_neutral(self):
        self.assertNotIn("jellyfin_item_id", PLAYBACK.lower())
        self.assertNotIn("jellyfin_item_id", SOURCE.lower())
        tree = ast.parse(PLAYBACK)
        identity = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "identity_matches")
        self.assertEqual([a.arg for a in identity.args.args], ["data", "imdb_id", "season", "episode"])

    def test_ams_progress_payload_is_provider_neutral(self):
        self.assertNotIn("jellyfin_item_id", AMS.lower())
        self.assertIn('"canonical_id": str(imdb_id)', AMS)
        self.assertIn('"imdb_id": str(imdb_id)', AMS)

    def test_progress_ignores_legacy_provider_column(self):
        self.assertNotIn("jellyfin_synced_position", PROGRESS.lower())
        # Existing user DBs can retain an old extra column. INSERT/SELECT must
        # continue to work because Apollo now addresses provider-neutral fields.
        with tempfile.NamedTemporaryFile(suffix=".db") as handle:
            db = sqlite3.connect(handle.name)
            db.execute("""
                CREATE TABLE progress (
                    media_key TEXT PRIMARY KEY,
                    imdb_id TEXT NOT NULL,
                    media_type TEXT NOT NULL,
                    season INTEGER NOT NULL DEFAULT 0,
                    episode INTEGER NOT NULL DEFAULT 0,
                    title TEXT NOT NULL,
                    position REAL NOT NULL,
                    duration REAL NOT NULL,
                    updated REAL NOT NULL,
                    authority_version INTEGER NOT NULL DEFAULT 1,
                    jellyfin_synced_position REAL NOT NULL DEFAULT -1
                )
            """)
            db.execute("""
                INSERT OR REPLACE INTO progress
                (media_key, imdb_id, media_type, season, episode, title, position, duration,
                 updated, authority_version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, ("tt1:0:0", "tt1", "movie", 0, 0, "Movie", 30.0, 100.0, 1.0))
            row = db.execute("SELECT imdb_id, position, jellyfin_synced_position FROM progress").fetchone()
            self.assertEqual(row, ("tt1", 30.0, -1.0))


if __name__ == "__main__":
    unittest.main()
