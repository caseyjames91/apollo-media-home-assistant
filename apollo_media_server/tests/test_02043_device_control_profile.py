import json
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.device import Device
from app.models.integration import Integration


def _client_with_android_tv():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(engine)

    integration_id = uuid.uuid4()
    device_id = uuid.uuid4()

    with SessionLocal() as db:
        integration = Integration(
            id=integration_id,
            kind="android_tv",
            name="Android TV",
            base_url="",
            config_json="{}",
        )
        device = Device(
            id=device_id,
            name="Bedroom Google TV",
            device_key=f"android_tv:{integration_id}:10.10.10.85:6466",
            device_type="android_tv",
            integration_id=integration_id,
            source_device_id="10.10.10.85:6466",
            capabilities_json=json.dumps(
                ["power", "navigation", "volume", "media", "launch_app"]
            ),
            config_json=json.dumps(
                {"host": "10.10.10.85", "port": 6466, "paired": True}
            ),
        )
        db.add_all([integration, device])
        db.commit()

    def override_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    return TestClient(app), device_id, SessionLocal, engine


def test_android_tv_control_profile_is_capability_driven():
    client, device_id, SessionLocal, engine = _client_with_android_tv()
    try:
        response = client.get(f"/devices/{device_id}/controls")
        assert response.status_code == 200

        body = response.json()
        assert body["device_id"] == str(device_id)
        assert body["integration_kind"] == "android_tv"
        assert body["launch_supported"] is True
        assert body["state_supported"] is True

        groups = {item["capability"]: item["commands"] for item in body["control_groups"]}

        assert groups["power"] == ["POWER"]
        assert groups["navigation"] == [
            "DPAD_UP",
            "DPAD_DOWN",
            "DPAD_LEFT",
            "DPAD_RIGHT",
            "DPAD_CENTER",
            "BACK",
            "HOME",
        ]
        assert groups["volume"] == ["VOLUME_UP", "VOLUME_DOWN", "MUTE"]
        assert groups["media"] == [
            "MEDIA_PLAY",
            "MEDIA_PAUSE",
            "MEDIA_PLAY_PAUSE",
            "MEDIA_STOP",
            "MEDIA_PREVIOUS",
            "MEDIA_NEXT",
        ]
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_android_tv_control_profile_respects_missing_capabilities():
    client, device_id, SessionLocal, engine = _client_with_android_tv()
    try:
        with SessionLocal() as db:
            device = db.get(Device, device_id)
            device.capabilities_json = json.dumps(["navigation"])
            db.commit()

        response = client.get(f"/devices/{device_id}/controls")
        assert response.status_code == 200

        body = response.json()
        assert body["launch_supported"] is False
        assert [item["capability"] for item in body["control_groups"]] == ["navigation"]
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
