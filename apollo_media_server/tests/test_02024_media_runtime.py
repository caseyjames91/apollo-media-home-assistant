from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEDIA = (ROOT / "app/api/media.py").read_text()


def test_media_dto_exposes_canonical_runtime():
    assert '"runtime_seconds": max(0, int(row.runtime_seconds or 0))' in MEDIA
