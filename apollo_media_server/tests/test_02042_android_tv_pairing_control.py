import json
import uuid
from pathlib import Path

import pytest
from androidtvremote2 import CannotConnect, ConnectionClosed

from app.integrations.registry import get_integration_type
from app.models.device import Device
from app.models.integration import Integration
from app.services import android_tv_control


class FakeRemote:
    instances = []

    def __init__(self, client_name, certfile, keyfile, host):
        self.client_name = client_name
        self.certfile = certfile
        self.keyfile = keyfile
        self.host = host
        self.generated = False
        self.pair_started = False
        self.finished_code = None
        self.commands = []
        self.launches = []
        self.disconnected = False
        self.connect_count = 0
        self.fail_next_command = False
        self.reconnecting = False
        self.availability_callback = None
        self.is_on = True
        self.current_app = "com.google.android.youtube.tv"
        self.volume_info = {"level": 10, "maximum": 25, "muted": False}
        self.device_info = {"model": "Google TV Streamer"}
        type(self).instances.append(self)

    async def async_generate_cert_if_missing(self):
        self.generated = True
        Path(self.certfile).write_text("CERT")
        Path(self.keyfile).write_text("KEY")
        return True

    async def async_start_pairing(self):
        self.pair_started = True

    async def async_finish_pairing(self, code):
        self.finished_code = code

    async def async_connect(self):
        self.connect_count += 1
        self.disconnected = False
        return None

    def add_is_available_updated_callback(self, callback):
        self.availability_callback = callback

    def keep_reconnecting(self):
        self.reconnecting = True

    def set_available(self, available):
        if self.availability_callback is not None:
            self.availability_callback(available)

    def send_key_command(self, command):
        if self.fail_next_command:
            self.fail_next_command = False
            raise ConnectionClosed()
        self.commands.append(command)

    def send_launch_app_command(self, target):
        self.launches.append(target)

    def disconnect(self):
        self.disconnected = True
        self.reconnecting = False


@pytest.fixture
def android_tv(monkeypatch, tmp_path):
    FakeRemote.instances.clear()
    android_tv_control._pairing_sessions.clear()
    android_tv_control.close_all_connections()
    monkeypatch.setattr(android_tv_control, "AndroidTVRemote", FakeRemote)
    monkeypatch.setattr(android_tv_control.settings, "data_dir", str(tmp_path))

    integration = Integration(
        id=uuid.uuid4(),
        kind="android_tv",
        name="Android TV",
        base_url="",
        config_json="{}",
    )
    device = Device(
        id=uuid.uuid4(),
        name="Living Room Google TV",
        device_key="android_tv:test:living-room",
        device_type="android_tv",
        integration_id=integration.id,
        source_device_id="10.10.10.50:6466",
        config_json=json.dumps(
            {
                "host": "10.10.10.50",
                "port": 6466,
                "model": "Google TV Streamer",
            }
        ),
        capabilities_json=json.dumps(
            ["power", "navigation", "volume", "media", "launch_app"]
        ),
    )
    yield integration, device
    android_tv_control.close_all_connections()


def test_android_tv_registry_marks_pairing_and_control():
    item = get_integration_type("android_tv")
    assert item is not None
    assert item.pairing is True
    assert item.control is True


@pytest.mark.asyncio
async def test_pairing_persists_shared_integration_credentials(android_tv):
    integration, device = android_tv

    await android_tv_control.start_pairing(integration, device)
    session = android_tv_control._pairing_sessions[device.id]
    assert session.remote.host == "10.10.10.50"
    assert Path(session.remote.certfile).exists()
    assert Path(session.remote.keyfile).exists()

    await android_tv_control.finish_pairing(device, "123456")
    assert device.id not in android_tv_control._pairing_sessions
    assert json.loads(device.config_json)["paired"] is True


@pytest.mark.asyncio
async def test_send_android_tv_key_reuses_connection(android_tv):
    integration, device = android_tv

    await android_tv_control.send_key(integration, device, "home")
    await android_tv_control.send_key(integration, device, "dpad_down")

    remote = FakeRemote.instances[-1]
    assert remote.commands == ["HOME", "DPAD_DOWN"]
    assert remote.connect_count == 1
    assert remote.disconnected is False
    assert remote.reconnecting is True
    assert android_tv_control._connections[device.id].available is True
    assert len(android_tv_control._connections) == 1


@pytest.mark.asyncio
async def test_reject_unknown_android_tv_key(android_tv):
    integration, device = android_tv
    with pytest.raises(ValueError):
        await android_tv_control.send_key(integration, device, "TOTALLY_FAKE")


@pytest.mark.asyncio
async def test_launch_android_tv_app_reuses_connection(android_tv, monkeypatch):
    integration, device = android_tv

    await android_tv_control.send_key(integration, device, "home")

    sleeps = []

    async def fake_sleep(delay):
        sleeps.append(delay)

    monkeypatch.setattr(android_tv_control.asyncio, "sleep", fake_sleep)

    await android_tv_control.launch(integration, device, "https://www.youtube.com")

    remote = FakeRemote.instances[-1]
    assert remote.commands == ["HOME"]
    assert remote.launches == ["https://www.youtube.com"]
    assert remote.connect_count == 1
    assert remote.disconnected is False
    assert sleeps == [0.1]


@pytest.mark.asyncio
async def test_read_android_tv_state_reuses_connection(android_tv):
    integration, device = android_tv

    first = await android_tv_control.get_state(integration, device)
    second = await android_tv_control.get_state(integration, device)

    remote = FakeRemote.instances[-1]
    assert first["available"] is True
    assert first["is_on"] is True
    assert first["current_app"] == "com.google.android.youtube.tv"
    assert first["volume"]["level"] == 10
    assert second["current_app"] == first["current_app"]
    assert remote.connect_count == 1
    assert remote.disconnected is False


@pytest.mark.asyncio
async def test_close_all_connections_disconnects_remote(android_tv):
    integration, device = android_tv

    await android_tv_control.send_key(integration, device, "home")
    remote = FakeRemote.instances[-1]
    assert remote.disconnected is False

    android_tv_control.close_all_connections()

    assert remote.disconnected is True
    assert android_tv_control._connections == {}


@pytest.mark.asyncio
async def test_android_tv_command_reconnects_after_connection_drop(android_tv):
    integration, device = android_tv

    await android_tv_control.send_key(integration, device, "home")
    remote = FakeRemote.instances[-1]
    assert remote.connect_count == 1

    remote.fail_next_command = True
    await android_tv_control.send_key(integration, device, "dpad_down")

    assert remote.connect_count == 2
    assert remote.commands == ["HOME", "DPAD_DOWN"]
    assert remote.disconnected is False
    assert remote.reconnecting is True
    assert android_tv_control._connections[device.id].available is True


@pytest.mark.asyncio
async def test_android_tv_native_availability_controls_state_and_commands(android_tv):
    integration, device = android_tv

    online = await android_tv_control.get_state(integration, device)
    remote = FakeRemote.instances[-1]
    assert online["available"] is True
    assert remote.reconnecting is True

    remote.set_available(False)

    offline = await android_tv_control.get_state(integration, device)
    assert offline == {
        "available": False,
        "is_on": None,
        "current_app": None,
        "volume": None,
        "device_info": None,
    }

    with pytest.raises(CannotConnect, match="unavailable"):
        await android_tv_control.send_key(integration, device, "home")

    remote.set_available(True)
    await android_tv_control.send_key(integration, device, "home")

    assert remote.connect_count == 1
    assert remote.commands == ["HOME"]


@pytest.mark.asyncio
async def test_close_device_connection_drops_only_requested_device(android_tv):
    integration, device = android_tv

    await android_tv_control.send_key(integration, device, "home")
    remote = FakeRemote.instances[-1]

    android_tv_control.close_device_connection(device.id)

    assert remote.disconnected is True
    assert device.id not in android_tv_control._connections
