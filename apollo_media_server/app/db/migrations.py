"""Lightweight, idempotent database migrations for Apollo Media Server.

AMS currently uses SQLite in Home Assistant add-on config storage.  SQLAlchemy's
``create_all`` creates missing tables, but it does not add columns to tables
that already exist.  These compatibility migrations preserve databases created
by AMS 0.1.x while bringing them up to the 0.2 schema expected by the ORM.
"""

from sqlalchemy import inspect
from sqlalchemy.engine import Engine


# Columns introduced by the Apollo-owned 0.2 data model.  SQLite accepts these
# ALTER TABLE ADD COLUMN definitions on an existing 0.1.x database.  Extra
# legacy columns are intentionally left in place so migration is non-destructive.
_REQUIRED_SQLITE_COLUMNS: dict[str, tuple[tuple[str, str], ...]] = {
    "profiles": (
        ("profile_type", "VARCHAR(24) NOT NULL DEFAULT 'adult'"),
        ("avatar", "VARCHAR(500)"),
        ("pin_required", "BOOLEAN NOT NULL DEFAULT 0"),
        # Added nullable first so existing SQLite rows can be backfilled safely.
        ("created_at", "DATETIME"),
    ),
    "media": (
        ("tvdb_id", "VARCHAR(32)"),
        ("series_title", "VARCHAR(500)"),
        ("year", "INTEGER"),
        ("runtime_seconds", "INTEGER"),
        ("overview", "TEXT"),
        ("poster_url", "VARCHAR(1000)"),
        ("backdrop_url", "VARCHAR(1000)"),
    ),
    "progress": (
        ("watched", "BOOLEAN NOT NULL DEFAULT 0"),
        ("watched_at", "DATETIME"),
    ),
    "integrations": (
        ("name", "VARCHAR(100) NOT NULL DEFAULT 'default'"),
    ),
}


def migrate_database(engine: Engine) -> None:
    """Bring an existing database up to the schema required by AMS 0.2.x.

    The migration is deliberately idempotent: every startup inspects the live
    schema and only adds missing pieces.  Fresh databases created from current
    models therefore pass through without changes.
    """

    if engine.dialect.name != "sqlite":
        # The Home Assistant add-on currently ships with SQLite.  Do not issue
        # SQLite-specific DDL against another database backend.
        return

    with engine.begin() as connection:
        inspector = inspect(connection)
        tables = set(inspector.get_table_names())

        for table_name, required_columns in _REQUIRED_SQLITE_COLUMNS.items():
            if table_name not in tables:
                continue

            existing = {column["name"] for column in inspector.get_columns(table_name)}
            for column_name, ddl in required_columns:
                if column_name in existing:
                    continue
                connection.exec_driver_sql(
                    f'ALTER TABLE "{table_name}" ADD COLUMN "{column_name}" {ddl}'
                )
                existing.add(column_name)

        # 0.1.x profiles predate created_at.  The ORM expects a real datetime on
        # reads, so backfill legacy rows after adding the column.
        if "profiles" in tables:
            profile_columns = {
                column["name"] for column in inspect(connection).get_columns("profiles")
            }
            if "created_at" in profile_columns:
                connection.exec_driver_sql(
                    "UPDATE profiles SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"
                )

        # Current media lookups mark provider IDs as indexed.  create_all() does
        # not add those indexes to an existing table, so create them explicitly.
        if "media" in tables:
            media_columns = {
                column["name"] for column in inspect(connection).get_columns("media")
            }
            for column_name in ("imdb_id", "tmdb_id", "tvdb_id"):
                if column_name in media_columns:
                    connection.exec_driver_sql(
                        f'CREATE INDEX IF NOT EXISTS "ix_media_{column_name}" '
                        f'ON media ("{column_name}")'
                    )
