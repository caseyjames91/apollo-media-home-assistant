import asyncio

from fastapi.testclient import TestClient

from app.integrations.registry import INTEGRATION_TYPES, get_integration_type
from app.main import app
from app.services.android_tv import AndroidTVDiscoveredDevice, android_tv_source_id, normalize_mac


def test_android_tv_is_first_generalized_controllable_integration():
    integration_type = get_integration_type("android_tv")
    assert integration_type is not None
    assert integration_type.discovery is True
    assert integration_type.pairing is True
    assert integration_type.control is True
    assert integration_type.requires_base_url is False
    assert integration_type.requires_access_token is False


def test_legacy_integration_types_remain_registered():
    assert {"jellyfin", "radarr", "sonarr", "tmdb"}.issubset(INTEGRATION_TYPES)


def test_jellyfin_registry_contract():
    integration_type = get_integration_type("jellyfin")
    assert integration_type is not None
    assert integration_type.requires_base_url is True
    assert integration_type.requires_access_token is True
    assert integration_type.discovery is False
    assert integration_type.pairing is False
    assert integration_type.control is False


def test_integration_types_endpoint_lists_android_tv():
    client = TestClient(app)
    response = client.get("/integrations/types")
    assert response.status_code == 200
    by_kind = {item["kind"]: item for item in response.json()}
    assert by_kind["android_tv"]["discovery"] is True
    assert by_kind["android_tv"]["pairing"] is True
    assert by_kind["android_tv"]["control"] is True


def test_android_tv_mac_identity_normalization():
    assert normalize_mac("B8:7B:D4:F1:F3:88") == "B8:7B:D4:F1:F3:88"
    assert normalize_mac("b8-7b-d4-f1-f3-88") == "B8:7B:D4:F1:F3:88"
    assert normalize_mac("not-a-mac") is None
    assert android_tv_source_id("B8:7B:D4:F1:F3:88") == "mac:b8:7b:d4:f1:f3:88"


def test_android_tv_discovery_endpoint(monkeypatch):
    async def fake_discover(timeout: float = 3.0):
        assert timeout == 1.5
        return [
            AndroidTVDiscoveredDevice(
                source_device_id="mac:b8:7b:d4:f1:f3:88",
                name="Living Room Google TV",
                host="10.10.10.50",
                port=6466,
                model="Google TV Streamer",
                mac="B8:7B:D4:F1:F3:88",
                certificate_name="Google TV Streamer",
                stable_identity=True,
            )
        ]

    monkeypatch.setattr(
        "app.api.integrations.discover_android_tv_devices",
        fake_discover,
    )

    client = TestClient(app)
    response = client.get("/integrations/android_tv/discover?timeout=1.5")
    assert response.status_code == 200
    assert response.json() == [
        {
            "source_device_id": "mac:b8:7b:d4:f1:f3:88",
            "name": "Living Room Google TV",
            "host": "10.10.10.50",
            "port": 6466,
            "model": "Google TV Streamer",
            "mac": "B8:7B:D4:F1:F3:88",
            "certificate_name": "Google TV Streamer",
            "stable_identity": True,
            "integration_kind": "android_tv",
        }
    ]


def test_non_discoverable_integration_rejected():
    client = TestClient(app)
    response = client.get("/integrations/tmdb/discover")
    assert response.status_code == 400



def test_list_integrations_does_not_hide_unregistered_persisted_rows():
    import uuid
    from app.api.integrations import list_integrations
    from app.models.integration import Integration

    row = Integration(
        id=uuid.uuid4(),
        kind="legacy_future_kind",
        name="default",
        base_url="",
        config_json="{}",
        enabled=True,
    )

    class FakeScalars:
        def __iter__(self):
            return iter([row])

    class FakeDB:
        def scalars(self, statement):
            return FakeScalars()

    result = list_integrations(FakeDB())
    assert len(result) == 1
    assert result[0].kind == "legacy_future_kind"
    assert result[0].name == "default"
