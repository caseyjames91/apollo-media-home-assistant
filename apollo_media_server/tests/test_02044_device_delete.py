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
from app.services import android_tv_control


def _client_with_device(monkeypatch):
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
        db.add(
            Integration(
                id=integration_id,
                kind="android_tv",
                name="Android TV",
                base_url="",
                config_json="{}",
            )
        )
        db.add(
            Device(
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
        )
        db.commit()

    def override_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    closed = []
    monkeypatch.setattr(
        android_tv_control,
        "close_device_connection",
        lambda target_id: closed.append(target_id),
    )
    return TestClient(app), device_id, SessionLocal, engine, closed


def test_delete_device_removes_record_and_closes_android_tv_connection(monkeypatch):
    client, device_id, SessionLocal, engine, closed = _client_with_device(monkeypatch)
    try:
        response = client.delete(f"/devices/{device_id}")
        assert response.status_code == 204

        with SessionLocal() as db:
            assert db.get(Device, device_id) is None

        assert closed == [device_id]
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_delete_unknown_device_returns_404(monkeypatch):
    client, _device_id, _SessionLocal, engine, closed = _client_with_device(monkeypatch)
    try:
        missing_id = uuid.uuid4()
        response = client.delete(f"/devices/{missing_id}")
        assert response.status_code == 404
        assert response.json()["detail"] == "device not found"
        assert closed == []
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
