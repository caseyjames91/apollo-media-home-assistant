import json
import os
import re

from .stream_identity import identity_aliases, release_key
from .stream_metadata import technical_info
import time

import xbmcvfs



def _technical_info(title="", description=""):
    return technical_info(title, description)

def _path():
    directory = xbmcvfs.translatePath("special://profile/addon_data/plugin.video.apollomedia")
    os.makedirs(directory, exist_ok=True)
    return os.path.join(directory, "source_session.json")



def _stream_key(stream):
    return release_key(stream or {})


def _flag_key(flag):
    stored = str((flag or {}).get("stream_key") or "").strip()
    return stored or _stream_key(flag or {})


def _flag_matches_stream(flag, stream):
    flag_aliases = set(identity_aliases(flag or {}))
    stream_aliases = set(identity_aliases(stream or {}))
    if flag_aliases & stream_aliases:
        return True

    flag_url = str((flag or {}).get("url") or "")
    stream_url = str((stream or {}).get("url") or "")
    return bool(flag_url and stream_url and flag_url == stream_url)

def _stream_flag(stream, flag_rows):
    for entry in flag_rows or []:
        if _flag_matches_stream(entry, stream):
            return entry
    return None


def _make_flag(stream, reason, created=None):
    return {
        "reason": reason,
        "url": str((stream or {}).get("url") or ""),
        "title": str((stream or {}).get("title") or ""),
        "provider": str((stream or {}).get("provider") or ""),
        "stream_key": _stream_key(stream or {}),
        "release_aliases": list(identity_aliases(stream or {})),
        "created": float(created or time.time()),
    }


def save(streams, imdb_id, media_type, season, episode, title, resume_position=0, resume_duration=0, jellyfin_item_id="", resume_mode="native"):
    old = load()
    same_identity = bool(
        old
        and str(old.get("imdb_id") or "").strip().lower() == str(imdb_id or "").strip().lower()
        and int(old.get("season") or 0) == int(season or 0)
        and int(old.get("episode") or 0) == int(episode or 0)
    )
    old_flags = list(old.get("flags") or []) if same_identity else []

    rows = [
        {
            "title": stream.title,
            "url": stream.url,
            "description": stream.description,
            "provider": getattr(stream, "provider", ""),
            "info_hash": getattr(stream, "info_hash", ""),
            "size": int(getattr(stream, "size", 0) or 0),
            "cached": getattr(stream, "cached", None),
            "playable": bool(getattr(stream, "playable", True)),
            "stream_key": release_key(stream),
            "release_aliases": list(identity_aliases(stream)),
            **_technical_info(stream.title, stream.description),
        }
        for stream in streams
    ]

    # Playback URLs can rotate between provider searches. Re-bind saved flags to
    # the newly returned URL using stable normalized release identity.
    flags = []
    for flag in old_flags:
        matching_row = next((row for row in rows if _flag_matches_stream(flag, row)), None)
        if matching_row:
            flags.append(_make_flag(
                matching_row,
                str(flag.get("reason") or "flagged"),
                flag.get("created"),
            ))
        else:
            retained = dict(flag)
            retained["stream_key"] = _flag_key(flag)
            retained["release_aliases"] = list(identity_aliases(flag))
            flags.append(retained)

    first_clean = -1
    for idx, row in enumerate(rows):
        if _stream_flag(row, flags) is None:
            first_clean = idx
            break

    data = {
        "created": time.time(),
        "index": first_clean,
        "imdb_id": imdb_id,
        "media_type": media_type,
        "season": int(season or 0),
        "episode": int(episode or 0),
        "title": title,
        "resume_position": float(resume_position or 0),
        "resume_duration": float(resume_duration or 0),
        "resume_mode": str(resume_mode or "native"),
        "jellyfin_item_id": str(jellyfin_item_id or ""),
        "streams": rows,
        "flags": flags,
        "attempts": {"state": "idle", "failed_keys": []},
    }
    with open(_path(), "w", encoding="utf-8") as handle:
        json.dump(data, handle)
    return data


def update_resume(position, duration=0, resume_mode="live"):
    data = load()
    if not data:
        return None
    data["resume_position"] = float(position or 0)
    data["resume_duration"] = float(duration or 0)
    data["resume_mode"] = str(resume_mode or "live")
    with open(_path(), "w", encoding="utf-8") as handle:
        json.dump(data, handle)
    return data


def load(max_age=21600):
    try:
        with open(_path(), "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if time.time() - float(data.get("created") or 0) > max_age:
            return None
        return data
    except Exception:
        return None


def current():
    data = load()
    if not data:
        return None
    streams = data.get("streams") or []
    raw_index = data.get("index")
    index = int(raw_index if raw_index is not None else -1)
    return streams[index] if 0 <= index < len(streams) else None


def _write(data):
    with open(_path(), "w", encoding="utf-8") as handle:
        json.dump(data, handle)
    return data


def begin_attempt(index=None, timeout=12.0, force_fail=False):
    data = load()
    if not data: return None
    streams = data.get("streams") or []
    raw_index = data.get("index") if index is None else index
    try: index = int(raw_index)
    except Exception: return None
    if not (0 <= index < len(streams)): return None
    attempts = dict(data.get("attempts") or {})
    attempts.update({"state":"requested","index":index,"stream_key":_stream_key(streams[index]),
        "requested_at":time.time(),"deadline":time.time()+max(1.0,float(timeout or 12.0)),
        "confirmed_at":0.0,"force_fail":bool(force_fail),
        "failed_keys":list(attempts.get("failed_keys") or [])})
    data["index"]=index; data["attempts"]=attempts
    return _write(data)


def start_attempt():
    data=load()
    if not data: return None
    attempts=dict(data.get("attempts") or {})
    if attempts.get("state")=="requested":
        attempts["state"]="started"
        attempts["started_at"]=time.time()
        data["attempts"]=attempts
        _write(data)
    return data


def confirm_attempt():
    data=load()
    if not data: return None
    attempts=dict(data.get("attempts") or {})
    if attempts.get("state") in ("requested", "started"):
        attempts["state"]="confirmed"; attempts["confirmed_at"]=time.time(); attempts["force_fail"]=False
        data["attempts"]=attempts; _write(data)
    return data


def fail_attempt(reason="startup_failure"):
    data=load()
    if not data: return None,None
    attempts=dict(data.get("attempts") or {}); streams=data.get("streams") or []
    try: index=int(attempts.get("index"))
    except Exception: return data,None
    if not (0 <= index < len(streams)): return data,None
    failed=set(attempts.get("failed_keys") or []); failed.update(identity_aliases(streams[index]))
    attempts.update({"state":"failed","failure_reason":str(reason or "startup_failure"),
        "failed_at":time.time(),"force_fail":False,"failed_keys":sorted(failed)})
    data["attempts"]=attempts; _write(data)
    data,stream=advance(failed_keys=failed)
    if not stream: return data,None
    attempts=dict(data.get("attempts") or {})
    attempts.update({"state":"retry_pending","index":int(data.get("index")),"stream_key":_stream_key(stream),
        "requested_at":0.0,"deadline":0.0,"confirmed_at":0.0,"force_fail":False,"failed_keys":sorted(failed)})
    data["attempts"]=attempts; _write(data)
    return data,stream


def attempt_state():
    return dict((load() or {}).get("attempts") or {})


def claim_pending_retry(settle_seconds=0.75, now=None):
    """Promote a settled retry_pending attempt to requested.

    fail_attempt() selects the replacement candidate, but automatic playback
    is deliberately launched later by the long-lived Kodi service after the
    failed player transaction has finished tearing down.
    """
    data = load()
    if not data:
        return None

    attempts = dict(data.get("attempts") or {})
    if attempts.get("state") != "retry_pending":
        return None

    try:
        failed_at = float(attempts.get("failed_at") or 0)
    except Exception:
        failed_at = 0.0

    current_time = time.time() if now is None else float(now)
    settle_seconds = max(0.0, float(settle_seconds or 0))

    if failed_at > 0 and current_time - failed_at < settle_seconds:
        return None

    try:
        index = int(attempts.get("index"))
    except Exception:
        return None

    streams = data.get("streams") or []
    if not (0 <= index < len(streams)):
        return None

    attempts.update({
        "state": "requested",
        "index": index,
        "stream_key": _stream_key(streams[index]),
        "requested_at": current_time,
        "deadline": current_time + 12.0,
        "confirmed_at": 0.0,
        "force_fail": False,
        "failed_keys": list(attempts.get("failed_keys") or []),
    })
    data["attempts"] = attempts
    _write(data)
    return index


def select(index):
    data = load()
    if not data:
        return None, None
    streams = data.get("streams") or []
    index = int(index)
    if index < 0 or index >= len(streams):
        return data, None
    data["index"] = index
    with open(_path(), "w", encoding="utf-8") as handle:
        json.dump(data, handle)
    return data, streams[index]



def _resolution_value(stream):
    quality = str((stream or {}).get("quality") or "").lower()
    if "2160" in quality or "4k" in quality:
        return 2160
    if "1080" in quality:
        return 1080
    if "720" in quality:
        return 720
    if "480" in quality or "sd" in quality:
        return 480
    return 0


def _candidate_indices(data, current_index, failed_keys=None):
    # One advancement policy for Try Next and upcoming automatic fallback:
    # same resolution first, then lower tiers, never wrap to higher/earlier.
    streams = data.get("streams") or []
    flags = list(data.get("flags") or [])
    failed_keys = set(failed_keys or ())
    if not (0 <= current_index < len(streams)):
        return []

    current_resolution = _resolution_value(streams[current_index])
    eligible = []
    for index in range(current_index + 1, len(streams)):
        stream = streams[index]
        if _stream_flag(stream, flags):
            continue
        if set(identity_aliases(stream)) & failed_keys:
            continue
        eligible.append(index)

    if current_resolution <= 0:
        return eligible

    same = [
        index for index in eligible
        if _resolution_value(streams[index]) == current_resolution
    ]
    lower = [
        index for index in eligible
        if 0 < _resolution_value(streams[index]) < current_resolution
    ]
    lower.sort(key=lambda index: (-_resolution_value(streams[index]), index))
    unknown = [
        index for index in eligible
        if _resolution_value(streams[index]) <= 0
    ]
    return same + lower + unknown


def advance(failed_keys=None):
    data = load()
    if not data:
        return None, None
    streams = data.get("streams") or []
    raw_index = data.get("index")
    current_index = int(raw_index if raw_index is not None else -1)
    candidates = _candidate_indices(data, current_index, failed_keys)
    if not candidates:
        return data, None
    next_index = candidates[0]
    data["index"] = next_index
    with open(_path(), "w", encoding="utf-8") as handle:
        json.dump(data, handle)
    return data, streams[next_index]


def flag(reason):
    data = load()
    if not data:
        return None
    streams = data.get("streams") or []
    raw_index = data.get("index")
    index = int(raw_index if raw_index is not None else -1)
    stream = streams[index] if 0 <= index < len(streams) else None
    if not stream:
        return data
    existing = [
        entry for entry in (data.get("flags") or [])
        if not _flag_matches_stream(entry, stream)
    ]
    existing.append(_make_flag(stream, reason))
    data["flags"] = existing
    with open(_path(), "w", encoding="utf-8") as handle:
        json.dump(data, handle)
    return data

































def flags():
    data = load() or {}
    return list(data.get("flags") or [])


def flag_for_url(url):
    target = str(url or "")
    data = load() or {}
    flag_rows = list(data.get("flags") or [])
    for entry in flag_rows:
        if str(entry.get("url") or "") == target:
            return entry
    stream = next(
        (row for row in (data.get("streams") or []) if str(row.get("url") or "") == target),
        None,
    )
    return _stream_flag(stream, flag_rows) if stream else None


def is_flagged(index):
    data = load()
    if not data:
        return False
    streams = data.get("streams") or []
    try:
        stream = streams[int(index)]
    except Exception:
        return False
    return _stream_flag(stream, data.get("flags") or []) is not None


def flag_index(index, reason):
    data = load()
    if not data:
        return None
    streams = data.get("streams") or []
    try:
        stream = streams[int(index)]
    except Exception:
        return None

    existing = [
        entry for entry in (data.get("flags") or [])
        if not _flag_matches_stream(entry, stream)
    ]
    existing.append(_make_flag(stream, reason))
    data["flags"] = existing

    with open(_path(), "w", encoding="utf-8") as handle:
        json.dump(data, handle)
    return stream


def unflag_index(index):
    data = load()
    if not data:
        return False
    streams = data.get("streams") or []
    try:
        stream = streams[int(index)]
    except Exception:
        return False

    old_flags = list(data.get("flags") or [])
    new_flags = [
        entry for entry in old_flags
        if not _flag_matches_stream(entry, stream)
    ]
    data["flags"] = new_flags

    with open(_path(), "w", encoding="utf-8") as handle:
        json.dump(data, handle)
    return len(new_flags) != len(old_flags)

def clear_resume(imdb_id, season=0, episode=0):
    data = load()
    if not data:
        return
    same_identity = (
        str(data.get("imdb_id") or "").strip().lower()
        == str(imdb_id or "").strip().lower()
        and int(data.get("season") or 0) == int(season or 0)
        and int(data.get("episode") or 0) == int(episode or 0)
    )
    if not same_identity:
        return
    data["resume_position"] = 0.0
    data["resume_duration"] = 0.0
    with open(_path(), "w", encoding="utf-8") as handle:
        json.dump(data, handle)
