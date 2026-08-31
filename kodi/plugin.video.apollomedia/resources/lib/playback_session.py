"""Canonical Apollo playback-session state.

This file contains no provider URLs.  It is the shared lifecycle contract
between source resolution and PlaybackMonitor, regardless of whether the
resolved URL came from local storage or a remote provider.
"""
import json
import os
import time

import xbmcvfs


MAX_AGE_SECONDS = 21600


def _path():
    directory = xbmcvfs.translatePath(
        "special://profile/addon_data/plugin.video.apollomedia"
    )
    os.makedirs(directory, exist_ok=True)
    return os.path.join(directory, "playback_session.json")


def _write(data):
    payload = dict(data or {})
    payload["updated"] = time.time()
    with open(_path(), "w", encoding="utf-8") as handle:
        json.dump(payload, handle)
    return payload


def save(source, imdb_id="", media_type="movie", season=0, episode=0,
         title="", requested_start_position=0,
         requested_duration=0, resume_mode="native"):
    return _write({
        "created": time.time(),
        "source": str(source or ""),
        "imdb_id": str(imdb_id or ""),
        "media_type": str(media_type or "movie"),
        "season": int(season or 0),
        "episode": int(episode or 0),
        "title": str(title or ""),
        "requested_start_position": float(requested_start_position or 0),
        "requested_duration": float(requested_duration or 0),
        "resume_mode": str(resume_mode or "native"),
        "start_applied": False,
        "last_position": 0.0,
        "last_duration": float(requested_duration or 0),
        "finished": False,
    })


def load(max_age=MAX_AGE_SECONDS):
    try:
        with open(_path(), "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if time.time() - float(data.get("updated") or data.get("created") or 0) > max_age:
            return {}
        return data
    except Exception:
        return {}


def identity_matches(data, imdb_id="", season=0, episode=0):
    data = data or {}
    wanted_imdb = str(imdb_id or "").strip().lower()
    actual_imdb = str(data.get("imdb_id") or "").strip().lower()
    return bool(
        wanted_imdb
        and actual_imdb
        and wanted_imdb == actual_imdb
        and int(data.get("season") or 0) == int(season or 0)
        and int(data.get("episode") or 0) == int(episode or 0)
    )


def checkpoint(position, duration=0):
    data = load()
    if not data:
        return {}
    data["last_position"] = max(0.0, float(position or 0))
    if float(duration or 0) > 0:
        data["last_duration"] = float(duration)
    return _write(data)


def request_start(position, duration=0, resume_mode="live"):
    data = load()
    if not data:
        return {}
    data["requested_start_position"] = max(0.0, float(position or 0))
    if float(duration or 0) > 0:
        data["requested_duration"] = float(duration)
    data["resume_mode"] = str(resume_mode or "live")
    data["start_applied"] = False
    data["finished"] = False
    return _write(data)


def mark_start_applied():
    data = load()
    if not data:
        return {}
    data["start_applied"] = True
    return _write(data)


def finish(position=0, duration=0, completed=False):
    data = load()
    if not data:
        return {}
    data["last_position"] = max(0.0, float(position or 0))
    if float(duration or 0) > 0:
        data["last_duration"] = float(duration)
    data["finished"] = True
    data["completed"] = bool(completed)
    return _write(data)
