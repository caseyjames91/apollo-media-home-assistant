import json
import time
import urllib.error
import urllib.request


def _base(addon):
    return str(addon.getSettingString("ams_url") or "").strip().rstrip("/")


def configured(addon):
    return bool(_base(addon))


def _request(addon, path, method="GET", payload=None, timeout=6):
    base = _base(addon)
    if not base:
        raise RuntimeError("AMS URL is not configured")
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        f"{base}/{str(path or '').lstrip('/')}",
        data=body,
        headers=headers,
        method=method,
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = response.read()
        if not data:
            return None
        return json.loads(data.decode("utf-8"))


def resolve_profile_id(addon):
    configured_id = str(addon.getSettingString("ams_profile_id") or "").strip()
    if configured_id:
        return configured_id
    profiles = _request(addon, "profiles") or []
    configured_name = str(addon.getSettingString("ams_profile") or "").strip().casefold()
    selected = None
    if configured_name:
        selected = next(
            (row for row in profiles if str(row.get("name") or "").strip().casefold() == configured_name),
            None,
        )
    if selected is None and len(profiles) == 1:
        selected = profiles[0]
    if not selected:
        raise RuntimeError("AMS profile is ambiguous; configure AMS profile in Apollo settings")
    return str(selected.get("id") or "")


def _iso_from_epoch(value):
    try:
        epoch = float(value or 0)
    except Exception:
        epoch = 0
    if epoch <= 0:
        epoch = time.time()
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))


def import_progress(addon, entries):
    profile_id = resolve_profile_id(addon)
    items = []
    for entry in entries or []:
        imdb = str(entry.get("imdb_id") or "").strip()
        if not imdb:
            continue
        season = int(entry.get("season") or 0)
        episode = int(entry.get("episode") or 0)
        items.append({
            "media_type": "episode" if (season or episode) else "movie",
            "canonical_id": imdb,
            "title": str(entry.get("title") or "Unknown"),
            "imdb_id": imdb,
            "season": season if (season or episode) else None,
            "episode": episode if (season or episode) else None,
            "position_seconds": max(0.0, float(entry.get("position") or 0)),
            "duration_seconds": max(0.0, float(entry.get("duration") or 0)),
            "updated_at": _iso_from_epoch(entry.get("updated")),
        })
    if not items:
        return {"status": "ok", "received": 0}
    return _request(addon, "progress/import", method="POST", payload={"profile_id": profile_id, "items": items}, timeout=10)


def report_progress(addon, imdb_id, media_type, season, episode, title, position, duration, updated=None, jellyfin_item_id=""):
    if not configured(addon) or not imdb_id:
        return False
    profile_id = resolve_profile_id(addon)
    season = int(season or 0)
    episode = int(episode or 0)
    payload = {
        "profile_id": profile_id,
        "media_type": "episode" if (season or episode) else str(media_type or "movie"),
        "canonical_id": str(imdb_id),
        "title": str(title or "Unknown"),
        "imdb_id": str(imdb_id),
        "jellyfin_item_id": str(jellyfin_item_id or "") or None,
        "season": season if (season or episode) else None,
        "episode": episode if (season or episode) else None,
        "position_seconds": max(0.0, float(position or 0)),
        "duration_seconds": max(0.0, float(duration or 0)),
        "updated_at": _iso_from_epoch(updated),
    }
    _request(addon, "progress", method="PUT", payload=payload, timeout=4)
    return True


def continue_watching(addon, local_progress=None, sync_jellyfin=True):
    if not configured(addon):
        return None
    if sync_jellyfin:
        try:
            _request(addon, "jellyfin/sync", method="POST", timeout=12)
        except Exception:
            # Last-known-good AMS state remains useful when Jellyfin is offline.
            pass
    if local_progress:
        try:
            import_progress(addon, local_progress)
        except Exception:
            pass
    profile_id = resolve_profile_id(addon)
    rows = _request(addon, f"profiles/{profile_id}/continue-watching", timeout=8)
    return rows if isinstance(rows, list) else []
