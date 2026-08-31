import os
import sqlite3
import time

import xbmcvfs


def _connect():
    directory = xbmcvfs.translatePath("special://profile/addon_data/plugin.video.apollomedia")
    os.makedirs(directory, exist_ok=True)
    connection = sqlite3.connect(os.path.join(directory, "apollo_progress.db"))
    connection.execute("""
        CREATE TABLE IF NOT EXISTS progress (
            media_key TEXT PRIMARY KEY,
            imdb_id TEXT NOT NULL,
            media_type TEXT NOT NULL,
            season INTEGER NOT NULL DEFAULT 0,
            episode INTEGER NOT NULL DEFAULT 0,
            title TEXT NOT NULL,
            position REAL NOT NULL,
            duration REAL NOT NULL,
            updated REAL NOT NULL,
            authority_version INTEGER NOT NULL DEFAULT 1
        )
    """)
    columns = {
        row[1] for row in connection.execute("PRAGMA table_info(progress)").fetchall()
    }
    if "authority_version" not in columns:
        connection.execute(
            "ALTER TABLE progress ADD COLUMN authority_version INTEGER NOT NULL DEFAULT 0"
        )
    # Older databases may still contain retired provider-specific columns.
    # They are intentionally ignored; Apollo progress is provider-neutral.
    return connection


def key(imdb_id, season=0, episode=0):
    return f"{imdb_id}:{int(season or 0)}:{int(episode or 0)}"


def save(imdb_id, media_type, season, episode, title, position, duration, updated=None):
    if not imdb_id or position < 10:
        return
    with _connect() as connection:
        connection.execute(
            """INSERT OR REPLACE INTO progress
               (media_key, imdb_id, media_type, season, episode, title, position, duration,
                updated, authority_version)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
            (key(imdb_id, season, episode), imdb_id, media_type, int(season or 0),
             int(episode or 0), title or "Unknown", float(position), float(duration),
             float(updated if updated is not None else time.time())),
        )


def remove(imdb_id, season=0, episode=0):
    with _connect() as connection:
        connection.execute("DELETE FROM progress WHERE media_key = ?", (key(imdb_id, season, episode),))


def get(imdb_id, season=0, episode=0):
    with _connect() as connection:
        row = connection.execute(
            "SELECT imdb_id, media_type, season, episode, title, position, duration, updated, authority_version FROM progress WHERE media_key = ?",
            (key(imdb_id, season, episode),),
        ).fetchone()
    if not row:
        return None
    names = ("imdb_id", "media_type", "season", "episode", "title", "position", "duration", "updated", "authority_version")
    return dict(zip(names, row))


def recent(limit=50):
    with _connect() as connection:
        rows = connection.execute(
            "SELECT imdb_id, media_type, season, episode, title, position, duration, updated, authority_version FROM progress ORDER BY updated DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
    names = ("imdb_id", "media_type", "season", "episode", "title", "position", "duration", "updated", "authority_version")
    return [dict(zip(names, row)) for row in rows]
