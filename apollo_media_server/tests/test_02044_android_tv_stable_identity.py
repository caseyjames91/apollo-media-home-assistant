import json
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal, init_db
from app.main import app
from app.models.device import Device
from app.models.integration import Integration
from app.models.room import Room


# These tests use SessionLocal directly before issuing API requests.
# Initialize the disposable SQLite database explicitly.
init_db()


def test_android_tv_mac_import_migrates_legacy_host_identity_in_place():
    integration_id = uuid.uuid4()
    room_id = uuid.uuid4()
    device_id = uuid.uuid4()
    legacy_source = "10.10.10.85:6466"

    with SessionLocal() as db:
        integration = Integration(
            id=integration_id,
            kind="android_tv",
            name=f"Android TV identity test {integration_id}",
            base_url="",
            config_json="{}",
        )
        room = Room(id=room_id, name=f"Identity Room {room_id}")
        device = Device(
            id=device_id,
            name="My Bedroom TV",
            device_key=f"android_tv:{integration_id}:{legacy_source}",
            device_type="android_tv",
            integration_id=integration_id,
            source_device_id=legacy_source,
            source_name="Bedroom Google TV",
            room_id=room_id,
            capabilities_json=json.dumps(["power", "navigation"]),
            config_json=json.dumps({"host": "10.10.10.85", "port": 6466}),
        )
        db.add_all([integration, room, device])
        db.commit()

    client = TestClient(app)
    response = client.post(
        "/devices/import",
        json={
            "integration_id": str(integration_id),
            "source_device_id": "mac:b8:7b:d4:f1:f3:88",
            "name": "Bedroom Google TV",
            "source_name": "Bedroom Google TV",
            "device_type": "android_tv",
            "capabilities": ["power", "navigation", "volume", "media", "launch_app"],
            "config": {
                "host": "10.10.10.85",
                "port": 6466,
                "mac": "B8:7B:D4:F1:F3:88",
            },
            "enabled": True,
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()

    assert body["id"] == str(device_id)
    assert body["source_device_id"] == "mac:b8:7b:d4:f1:f3:88"
    assert body["device_key"] == f"android_tv:{integration_id}:mac:b8:7b:d4:f1:f3:88"

    assert body["name"] == "My Bedroom TV"
    assert body["room_id"] == str(room_id)

    assert body["config"]["host"] == "10.10.10.85"
    assert body["config"]["port"] == 6466
    assert body["config"]["mac"] == "B8:7B:D4:F1:F3:88"

    with SessionLocal() as db:
        rows = list(db.scalars(select(Device).where(Device.integration_id == integration_id)))
        assert len(rows) == 1
        assert rows[0].id == device_id

        db.delete(rows[0])
        room = db.get(Room, room_id)
        if room is not None:
            db.delete(room)
        integration = db.get(Integration, integration_id)
        if integration is not None:
            db.delete(integration)
        db.commit()


def test_android_tv_mac_reimport_updates_host_without_changing_identity():
    integration_id = uuid.uuid4()
    device_id = uuid.uuid4()
    stable_source = "mac:b8:7b:d4:f1:f3:88"

    with SessionLocal() as db:
        integration = Integration(
            id=integration_id,
            kind="android_tv",
            name=f"Android TV readdress test {integration_id}",
            base_url="",
            config_json="{}",
        )
        device = Device(
            id=device_id,
            name="Bedroom Google TV",
            device_key=f"android_tv:{integration_id}:{stable_source}",
            device_type="android_tv",
            integration_id=integration_id,
            source_device_id=stable_source,
            source_name="Bedroom Google TV",
            capabilities_json="[]",
            config_json=json.dumps(
                {
                    "host": "10.10.10.85",
                    "port": 6466,
                    "mac": "B8:7B:D4:F1:F3:88",
                }
            ),
        )
        db.add_all([integration, device])
        db.commit()

    client = TestClient(app)
    response = client.post(
        "/devices/import",
        json={
            "integration_id": str(integration_id),
            "source_device_id": stable_source,
            "name": "Bedroom Google TV",
            "source_name": "Bedroom Google TV",
            "device_type": "android_tv",
            "capabilities": ["power"],
            "config": {
                "host": "10.10.10.222",
                "port": 6466,
                "mac": "B8:7B:D4:F1:F3:88",
            },
            "enabled": True,
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == str(device_id)
    assert body["source_device_id"] == stable_source
    assert body["config"]["host"] == "10.10.10.222"

    with SessionLocal() as db:
        rows = list(db.scalars(select(Device).where(Device.integration_id == integration_id)))
        assert len(rows) == 1
        db.delete(rows[0])
        integration = db.get(Integration, integration_id)
        if integration is not None:
            db.delete(integration)
        db.commit()
