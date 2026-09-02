import json
import time
import urllib.request
from urllib.parse import urlencode


def _base(addon):
    return str(addon.getSettingString("ams_url") or "").strip().rstrip("/")


def configured(addon):
    return bool(_base(addon))


def request(addon, path, method="GET", payload=None, timeout=8):
    base = _base(addon)
    if not base:
        raise RuntimeError("AMS URL is not configured")
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        f"{base}/{str(path or '').lstrip('/')}",
        data=data,
        headers=headers,
        method=method,
    )
    started = time.monotonic()
    with urllib.request.urlopen(req, timeout=timeout) as response:
        body = response.read()
        result = json.loads(body.decode("utf-8")) if body else None
    try:
        import xbmc
        xbmc.log(
            f"[ApolloPerf] AMS {method} {path}: {time.monotonic()-started:.3f}s",
            xbmc.LOGINFO,
        )
    except Exception:
        pass
    return result


_profile_id_cache = None


def profile_id(addon):
    global _profile_id_cache
    if _profile_id_cache:
        return _profile_id_cache

    explicit = str(addon.getSettingString("ams_profile_id") or "").strip()
    if explicit:
        _profile_id_cache = explicit
        return explicit

    rows = request(addon, "profiles") or []
    wanted = str(addon.getSettingString("ams_profile") or "").strip().casefold()
    if wanted:
        for row in rows:
            if str(row.get("name") or "").strip().casefold() == wanted:
                _profile_id_cache = str(row.get("id") or "")
                return _profile_id_cache

    if len(rows) == 1:
        _profile_id_cache = str(rows[0].get("id") or "")
        return _profile_id_cache

    raise RuntimeError("Configure an AMS Profile ID or unambiguous profile name")


def media(
    addon,
    media_type="",
    available_locally=None,
    canonical_id="",
    imdb_id="",
    season=None,
):
    params = {}
    if media_type:
        params["media_type"] = media_type
    if available_locally is not None:
        params["available_locally"] = "true" if available_locally else "false"
    if canonical_id:
        params["canonical_id"] = canonical_id
    if imdb_id:
        params["imdb_id"] = imdb_id
    if season is not None:
        params["season"] = int(season)
    path = "media"
    if params:
        path += "?" + urlencode(params)
    rows = request(addon, path, timeout=12) or []
    return rows if isinstance(rows, list) else []



_progress_cache = {}
_progress_index_cache = {}


def progress_rows(addon):
    pid = profile_id(addon)
    cached = _progress_cache.get(pid)
    if cached is not None:
        return cached
    rows = request(addon, f"profiles/{pid}/progress", timeout=10) or []
    rows = rows if isinstance(rows, list) else []
    _progress_cache[pid] = rows
    return rows


def _progress_value(progress):
    if not progress:
        return 0.0, 0.0, False
    return (
        max(0.0, float(progress.get("position_seconds") or 0)),
        max(0.0, float(progress.get("duration_seconds") or 0)),
        bool(progress.get("watched")),
    )


def progress_index(addon):
    """Build O(1) profile progress lookup maps once per plugin invocation."""
    pid = profile_id(addon)
    cached = _progress_index_cache.get(pid)
    if cached is not None:
        return cached

    by_media_id = {}
    by_canonical = {}
    by_imdb = {}

    for progress in progress_rows(addon):
        season = int(progress.get("season") or 0)
        episode = int(progress.get("episode") or 0)

        media_id = str(progress.get("media_id") or "").strip()
        if media_id:
            by_media_id[media_id] = progress

        canonical = str(progress.get("canonical_id") or "").strip().casefold()
        if canonical:
            by_canonical[(canonical, season, episode)] = progress

        imdb = str(progress.get("imdb_id") or "").strip().casefold()
        if imdb:
            by_imdb[(imdb, season, episode)] = progress

    cached = {
        "media_id": by_media_id,
        "canonical": by_canonical,
        "imdb": by_imdb,
    }
    _progress_index_cache[pid] = cached
    return cached


def progress_for(addon, row, season=0, episode=0):
    media_id = str(row.get("media_id") or row.get("id") or "").strip()
    canonical = str(row.get("canonical_id") or "").strip().casefold()
    imdb = str(row.get("imdb_id") or "").strip().casefold()
    season = int(season or row.get("season") or 0)
    episode = int(episode or row.get("episode") or 0)

    index = progress_index(addon)

    if media_id:
        progress = index["media_id"].get(media_id)
        if progress is not None:
            return _progress_value(progress)

    if canonical:
        progress = index["canonical"].get((canonical, season, episode))
        if progress is not None:
            return _progress_value(progress)

    if imdb:
        progress = index["imdb"].get((imdb, season, episode))
        if progress is not None:
            return _progress_value(progress)

    return 0.0, 0.0, False


def resolve_playback_identity(addon, media_id):
    media_id = str(media_id or "").strip()
    if not media_id:
        return {}
    result = request(addon, f"media/{media_id}/playback-identity", timeout=15) or {}
    return result if isinstance(result, dict) else {}


def continue_watching(addon):
    rows = request(addon, f"profiles/{profile_id(addon)}/continue-watching", timeout=10) or []
    return rows if isinstance(rows, list) else []


def resume(addon, imdb_id, season=0, episode=0):
    target = str(imdb_id or "").strip().casefold()
    season = int(season or 0)
    episode = int(episode or 0)
    if not target:
        return 0.0, 0.0
    for row in progress_rows(addon):
        if str(row.get("imdb_id") or "").strip().casefold() != target:
            continue
        if int(row.get("season") or 0) != season:
            continue
        if int(row.get("episode") or 0) != episode:
            continue
        return (
            max(0.0, float(row.get("position_seconds") or 0)),
            max(0.0, float(row.get("duration_seconds") or 0)),
        )
    return 0.0, 0.0


def playback_resolution(addon, media_id):
    device_key = str(addon.getSettingString("ams_device_key") or "").strip()
    if not device_key:
        raise RuntimeError("AMS Device Key is not configured")
    query = urlencode({"device_key": device_key})
    return request(addon, f"media/{media_id}/playback-resolution?{query}", timeout=10) or {}


def report_progress(addon, canonical_id, imdb_id, media_type, season, episode, title, position, duration):
    if not configured(addon) or not canonical_id:
        return
    season = int(season or 0)
    episode = int(episode or 0)
    payload = {
        "profile_id": profile_id(addon),
        "media_type": "episode" if episode > 0 else str(media_type or "movie"),
        "canonical_id": str(canonical_id),
        "title": str(title or "Unknown"),
        "imdb_id": str(imdb_id),
        "season": season if episode > 0 else None,
        "episode": episode if episode > 0 else None,
        "position_seconds": max(0.0, float(position or 0)),
        "duration_seconds": max(0.0, float(duration or 0)),
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    request(addon, "progress", method="PUT", payload=payload, timeout=5)


def discovery_show(addon, tmdb_id):
    tmdb_id = str(tmdb_id or "").strip()
    if not tmdb_id: raise RuntimeError("Discovery show requires a TMDB identity")
    result = request(addon, f"discovery/show/{tmdb_id}", timeout=20) or {}
    return result if isinstance(result, dict) else {}

def discovery_season(addon, tmdb_id, season):
    tmdb_id = str(tmdb_id or "").strip()
    if not tmdb_id: raise RuntimeError("Discovery season requires a TMDB identity")
    result = request(addon, f"discovery/show/{tmdb_id}/season/{int(season)}", timeout=20) or {}
    return result if isinstance(result, dict) else {}

def discovery(addon, mode, media_type, query="", page=1):
    mode = str(mode or "").strip().lower()
    media_type = str(media_type or "").strip().lower()
    if mode not in {"popular", "trending", "search"}:
        raise RuntimeError(f"Unsupported discovery mode: {mode}")
    path = f"discovery/{mode}/{media_type}"
    params={"page":max(1,int(page or 1))}
    if mode == "search":
        params["q"]=str(query or "").strip()
    path += "?" + urlencode(params)
    rows = request(addon, path, timeout=20) or []
    return rows if isinstance(rows, list) else []
