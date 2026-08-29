import json
import os
import re
import time

import xbmcvfs


def _technical_info(title="", description=""):
    text = f"{title} {description}".lower()

    if any(marker in text for marker in ("2160", "4k", "uhd")):
        quality = "4K / 2160p"
    elif "1080" in text:
        quality = "1080p"
    elif "720" in text:
        quality = "720p"
    elif any(marker in f" {text} " for marker in (" 480", " sd ")):
        quality = "SD / 480p"
    else:
        quality = "Other"

    video_bits = [quality]
    if any(marker in f" {text} " for marker in ("dolby vision", "dovi", " dv ")):
        video_bits.append("Dolby Vision")
    elif "hdr10+" in text or "hdr10plus" in text:
        video_bits.append("HDR10+")
    elif "hdr10" in text or " hdr " in f" {text} ":
        video_bits.append("HDR")
    if any(marker in text for marker in ("hevc", "h265", "h.265", "x265")):
        video_bits.append("HEVC")
    elif any(marker in text for marker in ("av1", "av01")):
        video_bits.append("AV1")
    elif any(marker in text for marker in ("h264", "h.264", "x264", "avc")):
        video_bits.append("H.264")

    audio = ""
    if "truehd" in text:
        audio = "TrueHD"
    elif any(marker in text for marker in ("eac3", "e-ac-3", "ddp", "dd+")):
        audio = "Dolby Digital Plus"
    elif any(marker in text for marker in ("ac3", "ac-3")):
        audio = "Dolby Digital"
    elif any(marker in text for marker in ("dts-hd", "dtshd", "dts:x", "dtsx")):
        audio = "DTS-HD"
    elif " dts" in f" {text} ":
        audio = "DTS"
    elif " aac" in f" {text} ":
        audio = "AAC"

    if "atmos" in text:
        audio = f"{audio} · Atmos" if audio else "Atmos"

    channel_match = re.search(r"(?<!\d)([257])\s*[.]\s*1(?!\d)", text)
    if channel_match:
        channels = f"{channel_match.group(1)}.1"
        audio = f"{audio} · {channels}" if audio else channels

    return {
        "quality": quality,
        "video": " · ".join(dict.fromkeys(video_bits)),
        "audio": audio or "Unknown audio",
    }


def _path():
    directory = xbmcvfs.translatePath("special://profile/addon_data/plugin.video.apollomedia")
    os.makedirs(directory, exist_ok=True)
    return os.path.join(directory, "source_session.json")


def save(streams, imdb_id, media_type, season, episode, title, resume_position=0, resume_duration=0, jellyfin_item_id="", resume_mode="native"):
    old = load()
    same_identity = bool(
        old
        and str(old.get("imdb_id") or "").strip().lower() == str(imdb_id or "").strip().lower()
        and int(old.get("season") or 0) == int(season or 0)
        and int(old.get("episode") or 0) == int(episode or 0)
    )
    flags = list(old.get("flags") or []) if same_identity else []

    rows = [
        {
            "title": stream.title,
            "url": stream.url,
            "description": stream.description,
            "provider": getattr(stream, "provider", ""),
            **_technical_info(stream.title, stream.description),
        }
        for stream in streams
    ]

    flagged_urls = {str(flag.get("url") or "") for flag in flags}
    first_clean = 0
    for idx, row in enumerate(rows):
        if str(row.get("url") or "") not in flagged_urls:
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
    index = int(data.get("index") or 0)
    return streams[index] if 0 <= index < len(streams) else None


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


def advance():
    data = load()
    if not data:
        return None, None
    streams = data.get("streams") or []
    next_index = int(data.get("index") or 0) + 1
    flagged_urls = {flag.get("url") for flag in data.get("flags", [])}
    while next_index < len(streams) and streams[next_index].get("url") in flagged_urls:
        next_index += 1
    if next_index >= len(streams):
        return data, None
    data["index"] = next_index
    with open(_path(), "w", encoding="utf-8") as handle:
        json.dump(data, handle)
    return data, streams[next_index]


def flag(reason):
    data = load()
    if not data:
        return None
    stream = current()
    if not stream:
        return data
    data.setdefault("flags", []).append({
        "reason": reason,
        "url": stream.get("url"),
        "title": stream.get("title"),
        "created": time.time(),
    })
    with open(_path(), "w", encoding="utf-8") as handle:
        json.dump(data, handle)
    return data

































def flags():
    data = load() or {}
    return list(data.get("flags") or [])


def flag_for_url(url):
    target = str(url or "")
    for entry in flags():
        if str(entry.get("url") or "") == target:
            return entry
    return None


def is_flagged(index):
    data = load()
    if not data:
        return False
    streams = data.get("streams") or []
    try:
        stream = streams[int(index)]
    except Exception:
        return False
    return flag_for_url(stream.get("url") or "") is not None


def flag_index(index, reason):
    data = load()
    if not data:
        return None
    streams = data.get("streams") or []
    try:
        stream = streams[int(index)]
    except Exception:
        return None

    url = str(stream.get("url") or "")
    existing = [
        entry for entry in (data.get("flags") or [])
        if str(entry.get("url") or "") != url
    ]
    existing.append({
        "reason": reason,
        "url": url,
        "title": stream.get("title"),
        "created": time.time(),
    })
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

    url = str(stream.get("url") or "")
    old_flags = list(data.get("flags") or [])
    new_flags = [
        entry for entry in old_flags
        if str(entry.get("url") or "") != url
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
