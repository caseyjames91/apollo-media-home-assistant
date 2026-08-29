import base64
import concurrent.futures
import json
import re
import urllib.parse
from dataclasses import dataclass

from .http import get_json


COMET_URL = "https://comet.elfhosted.com"
TORRENTIO_URL = "https://torrentio.strem.fun"


@dataclass
class Stream:
    title: str
    url: str
    description: str = ""
    provider: str = ""


def stream_id(imdb_id, media_type, season=None, episode=None):
    if media_type == "series" and season is not None and episode is not None:
        return f"{imdb_id}:{season}:{episode}"
    return imdb_id


def comet(token, imdb_id, media_type, season=None, episode=None):
    config = base64.b64encode(json.dumps({
        "debridService": "torbox",
        "debridApiKey": token,
        "cachedOnly": True,
    }).encode("utf-8")).decode("ascii")

    identifier = stream_id(imdb_id, media_type, season, episode)
    data = get_json(
        f"{COMET_URL}/{config}/stream/{media_type}/{identifier}.json",
        timeout=60,
    )

    return [
        Stream(
            (entry.get("name") or entry.get("title") or "Remote source").replace("\n", " "),
            entry.get("url") or "",
            f"[Comet] {(entry.get('description') or entry.get('title') or '').replace(chr(10), ' ')}",
            "comet",
        )
        for entry in data.get("streams", [])
        if entry.get("url")
    ]


def torrentio(token, imdb_id, media_type, season=None, episode=None):
    identifier = stream_id(imdb_id, media_type, season, episode)
    config = f"debridoptions=nodownloadlinks|torbox={token}"
    data = get_json(
        f"{TORRENTIO_URL}/{config}/stream/{media_type}/{identifier}.json",
        timeout=45,
    )

    streams = []
    for entry in data.get("streams", []):
        url = entry.get("url") or ""
        name = (entry.get("name") or "").replace("\n", " ")
        if not url or ("[tb+]" not in name.lower() and "⚡" not in name):
            continue

        description = (entry.get("title") or "").replace("\n", " ")
        filename = (
            (entry.get("behaviorHints") or {}).get("filename")
            or description
            or name
        )
        streams.append(Stream(
            filename,
            url,
            f"[Torrentio] {name} {description}",
            "torrentio",
        ))
    return streams


def _extract_stremio_addon_url(value):
    """
    Accept either:
      - a direct configured addon URL ending in /manifest.json
      - a configured addon root
      - a full Stremio web install URL containing ?addon=<encoded URL>
    """
    value = str(value or "").strip()
    if not value:
        return ""

    # Stremio web install links store the configured addon URL in the `addon`
    # query parameter after the hash route.
    if "addon=" in value:
        try:
            query_part = value.split("?", 1)[1]
            params = urllib.parse.parse_qs(query_part)
            addon_values = params.get("addon") or []
            if addon_values:
                value = addon_values[0]
        except Exception:
            pass

    value = urllib.parse.unquote(value).strip()

    if value.startswith("stremio://"):
        value = "https://" + value[len("stremio://"):]

    value = value.rstrip("/")
    if value.endswith("/manifest.json"):
        value = value[:-len("/manifest.json")]
    elif value.endswith("manifest.json"):
        value = value[:-len("manifest.json")].rstrip("/")

    return value.rstrip("/")


def debridio(addon_url, imdb_id, media_type, season=None, episode=None):
    """
    Query a configured Debridio Stremio addon.

    The user's configured addon URL already contains Debridio's provider
    configuration, including the selected debrid service. Apollo never embeds
    or logs that configuration into the source bundle.
    """
    addon_root = _extract_stremio_addon_url(addon_url)
    if not addon_root:
        return []

    identifier = stream_id(imdb_id, media_type, season, episode)
    data = get_json(
        f"{addon_root}/stream/{media_type}/{identifier}.json",
        timeout=60,
    )

    streams = []
    for entry in data.get("streams", []):
        url = entry.get("url") or ""
        if not url:
            continue

        name = (entry.get("name") or "").replace("\n", " ")
        title = (entry.get("title") or "").replace("\n", " ")
        filename = (
            (entry.get("behaviorHints") or {}).get("filename")
            or title
            or name
            or "Debridio source"
        )

        streams.append(Stream(
            filename,
            url,
            f"[Debridio] {name} {title}",
            "debridio",
        ))

    return streams



def score(stream, profile=None):
    profile = profile or {}
    text = f"{stream.title} {stream.description}".lower()
    points = 0
    if any(value in text for value in ("2160", "4k", "uhd")): points += 100000
    elif "1080" in text: points += 50000
    elif "720" in text: points += 20000
    if "remux" in text: points += 6000
    elif "bluray" in text or "blu-ray" in text: points += 4000
    elif any(value in text for value in ("web-dl", "webdl", "web dl")): points += 2000
    if any(value in text for value in ("dolby vision", "dovi", "hdr10", " hdr")): points += 500
    if any(value in text for value in ("truehd", "atmos", "dts-hd", "dtsx")): points += 200
    if any(value in f" {text} " for value in (" cam ", " ts ", "hdcam", "telesync")): points -= 100000
    checks = (
        ("allow_2160p", ("2160", "4k", "uhd")),
        ("allow_1080p", ("1080",)), ("allow_720p", ("720",)), ("allow_480p", ("480", " sd ")),
        ("allow_dolby_vision", ("dolby vision", "dovi", " dv ")),
        ("allow_hdr10plus", ("hdr10+", "hdr10plus")), ("allow_hlg", (" hlg",)),
        ("allow_av1", ("av1", "av01")), ("allow_hevc", ("hevc", "h265", "h.265", "x265")),
        ("allow_h264", ("h264", "h.264", "x264", "avc")), ("allow_mpeg2", ("mpeg2", "mpeg-2")),
        ("allow_vc1", ("vc-1", "vc1")), ("allow_truehd", ("truehd", "atmos")),
        ("allow_dtshd", ("dts-hd", "dtshd", "dts:x", "dtsx")),
        ("allow_eac3", ("eac3", "e-ac-3", "dd+")), ("allow_ac3", ("ac3", "ac-3")),
        ("allow_aac", (" aac",)),
    )
    detected = False
    for setting, markers in checks:
        if any(marker in f" {text} " for marker in markers):
            detected = True
            if profile.get(setting) is False:
                points -= 300000
    is_dv = any(value in f" {text} " for value in ("dolby vision", "dovi", " dv "))
    is_hdr10plus = "hdr10+" in text or "hdr10plus" in text
    is_hlg = " hlg" in f" {text} "
    is_hdr10 = not is_dv and not is_hdr10plus and not is_hlg and ("hdr10" in text or " hdr" in f" {text} ")
    if is_hdr10 and profile.get("allow_hdr10") is False:
        points -= 300000
    if not any((is_dv, is_hdr10plus, is_hlg, is_hdr10)) and profile.get("allow_sdr") is False:
        points -= 300000
    if not detected and profile.get("allow_unknown") is False:
        points -= 300000
    return points



def find_streams(
    token,
    enabled_providers,
    imdb_id,
    media_type,
    season=None,
    episode=None,
    profile=None,
    debridio_url="",
):
    """
    Query all enabled source providers concurrently, normalize their streams,
    dedupe the combined result, then run one common compatibility/ranking pass.
    """
    enabled = {
        str(provider).strip().lower()
        for provider in (enabled_providers or [])
        if str(provider).strip()
    }

    jobs = []
    if "comet" in enabled:
        jobs.append(("comet", comet, (token, imdb_id, media_type, season, episode)))
    if "torrentio" in enabled:
        jobs.append(("torrentio", torrentio, (token, imdb_id, media_type, season, episode)))
    if "debridio" in enabled and debridio_url:
        jobs.append((
            "debridio",
            debridio,
            (debridio_url, imdb_id, media_type, season, episode),
        ))

    if not jobs:
        return []

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        futures = [
            pool.submit(function, *args)
            for _, function, args in jobs
        ]
        for future in futures:
            try:
                results.extend(future.result())
            except Exception:
                # One provider failing must not take down the others.
                pass

    deduped = {}
    for stream in results:
        # Prefer filename-ish identity across providers. If two providers expose
        # the same release, Apollo only needs one playable candidate.
        key = re.sub(r"[^a-z0-9]", "", stream.title.lower()) or stream.url
        deduped.setdefault(key, stream)

    return sorted(
        deduped.values(),
        key=lambda stream: score(stream, profile),
        reverse=True,
    )
