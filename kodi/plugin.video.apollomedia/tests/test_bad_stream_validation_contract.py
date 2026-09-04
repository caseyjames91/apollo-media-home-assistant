from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICE = (ROOT / "service.py").read_text()
AMS = (ROOT / "resources/lib/ams.py").read_text()
MEDIA = (
    ROOT.parents[1] / "apollo_media_server/app/api/media.py"
).read_text()


def test_service_uses_shared_duration_validator():
    assert "from resources.lib.playback_validation import duration_valid" in SERVICE


def test_remote_progress_is_provisional_until_validated():
    assert 'if self.playback_mode == "remote":' in SERVICE
    assert "if decision is not True:" in SERVICE


def test_rejected_stream_suppresses_progress_before_stop():
    suppress = SERVICE.index("self.suppress_progress = True")
    stop = SERVICE.index("self.stop()", suppress)
    assert suppress < stop


def test_rejected_stream_is_persistently_flagged_and_advanced():
    assert 'source_session.flag("bad_stream")' in SERVICE
    assert "source_session.advance()" in SERVICE
    assert "action=play_session_stream&index=" in SERVICE


def test_service_uses_local_media_lookup_for_runtime():
    assert "identity = ams.media_item(ADDON, media_id)" in SERVICE
    assert 'result = request(addon, f"media/{media_id}", timeout=5)' in AMS


def test_media_dto_exposes_runtime():
    assert '"runtime_seconds": max(0, int(row.runtime_seconds or 0))' in MEDIA
