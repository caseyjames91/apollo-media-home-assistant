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



def _stream_text(stream):
    return f" {stream.title} {stream.description} ".lower()

def _has(text, values):
    return any(v in text for v in values)

def _resolution(text):
    if _has(text, ("2160","4k","uhd")): return 2160
    if "1080" in text: return 1080
    if "720" in text: return 720
    if _has(text, ("480"," sd ")): return 480
    return 0

def _csv(value):
    return tuple(x.strip().lower() for x in str(value or "").split(",") if x.strip())

def _languages(text):
    groups=(
        ("english",(r"\benglish\b",r"\beng\b")),
        ("spanish",(r"\bspanish\b",r"\bspa\b",r"\blatino\b")),
        ("french",(r"\bfrench\b",r"\bfre\b",r"\bfra\b")),
        ("german",(r"\bgerman\b",r"\bger\b",r"\bdeu\b")),
        ("italian",(r"\bitalian\b",r"\bita\b")),
        ("japanese",(r"\bjapanese\b",r"\bjpn\b")),
        ("korean",(r"\bkorean\b",r"\bkor\b")),
        ("hindi",(r"\bhindi\b",r"\bhin\b")),
        ("portuguese",(r"\bportuguese\b",r"\bpor\b",r"\bpt-br\b")),
        ("russian",(r"\brussian\b",r"\brus\b")),
    )
    return tuple(lang for lang, pats in groups if any(re.search(p,text,re.I) for p in pats))

def filter_reason(stream, profile=None):
    profile=profile or {}
    text=_stream_text(stream)
    if (
        re.search(r"(?<![a-z0-9])(?:hdcam|camrip|cam|telesync|telecine)(?![a-z0-9])", text, re.I)
        or re.search(r"(?<![a-z0-9])ts(?![a-z0-9])", text, re.I)
    ):
        return "cam_or_telesync"
    rs={2160:"allow_2160p",1080:"allow_1080p",720:"allow_720p",480:"allow_480p"}.get(_resolution(text))
    if rs and profile.get(rs) is False: return rs
    checks=(
        ("allow_dolby_vision",("dolby vision","dovi"," dv ")),
        ("allow_hdr10plus",("hdr10+","hdr10plus")),
        ("allow_hlg",(" hlg",)),
        ("allow_av1",("av1","av01")),
        ("allow_hevc",("hevc","h265","h.265","x265")),
        ("allow_h264",("h264","h.264","x264","avc")),
        ("allow_mpeg2",("mpeg2","mpeg-2")),
        ("allow_vc1",("vc-1","vc1")),
        ("allow_truehd",("truehd","atmos")),
        ("allow_dtshd",("dts-hd","dtshd","dts:x","dtsx")),
        ("allow_eac3",("eac3","e-ac-3","dd+")),
        ("allow_ac3",("ac3","ac-3")),
        ("allow_aac",(" aac",)),
    )
    detected=bool(_resolution(text))
    for setting,markers in checks:
        if _has(text,markers):
            detected=True
            if profile.get(setting) is False: return setting
    dv=_has(text,("dolby vision","dovi"," dv "))
    hp=_has(text,("hdr10+","hdr10plus"))
    hlg=" hlg" in text
    hdr10=not any((dv,hp,hlg)) and _has(text,("hdr10"," hdr "))
    if hdr10 and profile.get("allow_hdr10") is False: return "allow_hdr10"
    if not any((dv,hp,hlg,hdr10)) and profile.get("allow_sdr") is False: return "allow_sdr"
    if not detected and profile.get("allow_unknown") is False: return "allow_unknown"
    langs=set(_languages(text))
    excluded=set(_csv(profile.get("excluded_languages")))
    if langs & excluded: return "excluded_language"
    allowed=set(_csv(profile.get("allowed_languages")))
    if allowed and langs and not (langs & allowed): return "language_not_allowed"
    return None

def ranking_key(stream, profile=None):
    profile=profile or {}
    text=_stream_text(stream)
    resolution={2160:4,1080:3,720:2,480:1,0:0}[_resolution(text)]
    quality=4 if "remux" in text else 3 if _has(text,("bluray","blu-ray")) else 2 if _has(text,("web-dl","webdl","web dl")) else 1 if "webrip" in text else 0
    preferred=_csv(profile.get("preferred_languages"))
    langs=_languages(text)
    hits=[preferred.index(x) for x in langs if x in preferred]
    language=len(preferred)-min(hits) if hits else 0
    priority=_csv(profile.get("provider_priority")) or ("debridio","torrentio","comet")
    provider=len(priority)-priority.index(stream.provider.lower()) if stream.provider.lower() in priority else 0
    hdr=1 if _has(text,("dolby vision","dovi"," hdr","hlg")) else 0
    audio=1 if _has(text,("truehd","atmos","dts-hd","dts:x","dtsx")) else 0
    return (resolution,quality,language,provider,hdr,audio)

def score(stream, profile=None):
    if filter_reason(stream,profile): return -1
    return sum(v*w for v,w in zip(ranking_key(stream,profile),(100000,10000,1000,100,10,1)))

def rank_streams(streams, profile=None):
    eligible=[s for s in streams if filter_reason(s,profile) is None]
    eligible.sort(key=lambda s:(s.provider.lower(),s.title.casefold(),s.url))
    eligible.sort(key=lambda s:ranking_key(s,profile),reverse=True)
    return eligible

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

    return rank_streams(deduped.values(), profile)
