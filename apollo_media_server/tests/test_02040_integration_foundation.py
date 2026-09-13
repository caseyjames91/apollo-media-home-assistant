from pathlib import Path
import sqlite3


def test_generic_integration_model_contract():
    text = Path("app/models/integration.py").read_text()
    assert "refresh_token" in text
    assert "config_json" in text
    assert "created_at" in text
    assert "updated_at" in text
    assert 'default=""' in text


def test_unified_device_model_contract_preserves_legacy_registration():
    text = Path("app/models/device.py").read_text()
    for field in (
        "integration_id",
        "source_device_id",
        "source_name",
        "room_id",
        "capabilities_json",
        "config_json",
        "enabled",
    ):
        assert field in text
    assert "device_key" in text
    assert "device_type" in text
    assert "ha_entity_id" in text


def test_room_model_contract():
    text = Path("app/models/room.py").read_text()
    assert "class Room(Base)" in text
    assert "source_integration_id" in text
    assert "source_area_id" in text
    assert "sort_order" in text


def test_room_router_registered():
    text = Path("app/main.py").read_text()
    assert "app.include_router(rooms.router)" in text


def test_legacy_sqlite_accepts_additive_foundation_columns(tmp_path):
    database = tmp_path / "legacy.db"
    connection = sqlite3.connect(database)
    try:
        connection.execute(
            "CREATE TABLE integrations ("
            "id VARCHAR(32) PRIMARY KEY, kind VARCHAR(32) NOT NULL, "
            "name VARCHAR(100) NOT NULL DEFAULT 'default', "
            "base_url VARCHAR(500) NOT NULL, access_token TEXT, "
            "enabled BOOLEAN NOT NULL DEFAULT 1)"
        )
        connection.execute(
            "CREATE TABLE devices ("
            "id VARCHAR(32) PRIMARY KEY, name VARCHAR(100) NOT NULL, "
            "device_key VARCHAR(128) NOT NULL UNIQUE, "
            "device_type VARCHAR(32) NOT NULL, ha_entity_id VARCHAR(255), "
            "last_seen_at DATETIME NOT NULL)"
        )

        for ddl in (
            "ALTER TABLE integrations ADD COLUMN refresh_token TEXT",
            "ALTER TABLE integrations ADD COLUMN config_json TEXT NOT NULL DEFAULT '{}'",
            "ALTER TABLE integrations ADD COLUMN created_at DATETIME",
            "ALTER TABLE integrations ADD COLUMN updated_at DATETIME",
            "ALTER TABLE devices ADD COLUMN integration_id VARCHAR(32)",
            "ALTER TABLE devices ADD COLUMN source_device_id VARCHAR(255)",
            "ALTER TABLE devices ADD COLUMN source_name VARCHAR(255)",
            "ALTER TABLE devices ADD COLUMN room_id VARCHAR(32)",
            "ALTER TABLE devices ADD COLUMN capabilities_json TEXT NOT NULL DEFAULT '[]'",
            "ALTER TABLE devices ADD COLUMN config_json TEXT NOT NULL DEFAULT '{}'",
            "ALTER TABLE devices ADD COLUMN enabled BOOLEAN NOT NULL DEFAULT 1",
        ):
            connection.execute(ddl)
    finally:
        connection.close()
