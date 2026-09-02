import base64
import concurrent.futures
import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass

from .http import get_json
from .stream_identity import identity_aliases
from .stream_metadata import filter_reason, rank_streams, ranking_key, score


COMET_URL = "https://comet.elfhosted.com"
TORRENTIO_URL = "https://torrentio.strem.fun"


@dataclass
class Stream:
    title: str
    url: str
    description: str = ""
    provider: str = ""
    info_hash: str = ""
    size: int = 0
    cached: bool | None = None
    playable: bool = True


def _safe_int(value):
    try:
        return max(int(float(value or 0)), 0)
    except (TypeError, ValueError):
        return 0


def _stream_identity_fields(entry):
    hints = entry.get("behaviorHints") or {}
    return {
        "info_hash": entry.get("infoHash") or hints.get("infoHash") or "",
        "size": _safe_int(
            entry.get("size")
            or entry.get("videoSize")
            or hints.get("videoSize")
            or hints.get("size")
        ),
    }


VIDEO_EXTENSIONS = (".mkv", ".mp4", ".m4v", ".avi", ".mov", ".ts", ".m2ts", ".webm")
ARCHIVE_EXTENSIONS = (".rar", ".zip", ".7z", ".r00", ".r01", ".001")

def _file_name(row):
    if isinstance(row, str):
        return row
    if not isinstance(row, dict):
        return ""
    return str(row.get("name") or row.get("filename") or row.get("path") or "").strip()

def _cached_payload_for_hash(data, info_hash):
    target=str(info_hash or "").strip().lower()
    if not target or data is None:
        return None
    if isinstance(data, dict):
        for key,value in data.items():
            if str(key).strip().lower()==target:
                return value
        for value in data.values():
            found=_cached_payload_for_hash(value,target)
            if found is not None:
                return found
    elif isinstance(data,list):
        for value in data:
            if isinstance(value,dict):
                candidate=str(value.get("hash") or value.get("info_hash") or value.get("infoHash") or "").strip().lower()
                if candidate==target:
                    return value
    return None

def _cached_payload_playable(payload):
    if payload is None or payload is False:
        return False
    if payload is True:
        return True
    if not isinstance(payload,dict):
        return bool(payload)
    files=payload.get("files") or payload.get("file_list") or payload.get("filelist") or []
    if not files:
        return True
    names=[_file_name(row).lower() for row in files]
    names=[name for name in names if name]
    if not names:
        return True
    has_video=any(name.endswith(VIDEO_EXTENSIONS) for name in names)
    archive_only=all(name.endswith(ARCHIVE_EXTENSIONS) for name in names)
    return has_video and not archive_only

def torbox_cached_hashes(token, hashes):
    hashes=sorted({str(value or "").strip().lower() for value in hashes or [] if str(value or "").strip()})
    if not token or not hashes:
        return {}
    query=urllib.parse.urlencode([("hash",value) for value in hashes]+[("format","object"),("list_files","true")])
    request=urllib.request.Request(
        f"https://api.torbox.app/v1/api/torrents/checkcached?{query}",
        headers={"Accept":"application/json","Authorization":f"Bearer {token}","User-Agent":"ApolloMedia/0.10"},
    )
    with urllib.request.urlopen(request,timeout=20) as response:
        raw=json.loads(response.read().decode("utf-8")) or {}
    data=raw.get("data")
    return {value:_cached_payload_playable(_cached_payload_for_hash(data,value)) for value in hashes}

def _apply_cache_evidence(streams, token, provider_asserted=False):
    streams=list(streams or [])
    hashes=[stream.info_hash for stream in streams if stream.info_hash]
    checked={}
    if hashes:
        try:
            checked=torbox_cached_hashes(token,hashes)
        except Exception:
            checked={}
    for stream in streams:
        key=str(stream.info_hash or "").strip().lower()
        if key and key in checked:
            stream.cached=bool(checked[key]); stream.playable=bool(checked[key])
        elif provider_asserted:
            stream.cached=True
        else:
            stream.cached=None
    return streams

def _cached_playable_only(streams):
    return [stream for stream in streams if stream.cached is True and stream.playable is not False]

def stream_id(imdb_id, media_type, season=None, episode=None):
    if media_type == "series" and season is not None and episode is not None:
        return f"{imdb_id}:{season}:{episode}"
    return imdb_id


def comet(token, imdb_id, media_type, season=None, episode=None, cached_only=True):
    config = base64.b64encode(json.dumps({
        "debridService": "torbox",
        "debridApiKey": token,
        "cachedOnly": bool(cached_only),
    }).encode("utf-8")).decode("ascii")

    identifier = stream_id(imdb_id, media_type, season, episode)
    data = get_json(
        f"{COMET_URL}/{config}/stream/{media_type}/{identifier}.json",
        timeout=60,
    )

    streams = [
        Stream(
            (entry.get("name") or entry.get("title") or "Remote source").replace("\n", " "),
            entry.get("url") or "",
            f"[Comet] {(entry.get('description') or entry.get('title') or '').replace(chr(10), ' ')}",
            "comet",
            cached=True if cached_only else None,
            **_stream_identity_fields(entry),
        )
        for entry in data.get("streams", [])
        if entry.get("url")
    ]
    return _apply_cache_evidence(streams, token, provider_asserted=bool(cached_only))


def torrentio(token, imdb_id, media_type, season=None, episode=None, cached_only=True):
    identifier = stream_id(imdb_id, media_type, season, episode)
    config = f"debridoptions=nodownloadlinks|torbox={token}" if cached_only else f"torbox={token}"
    data = get_json(
        f"{TORRENTIO_URL}/{config}/stream/{media_type}/{identifier}.json",
        timeout=45,
    )

    streams = []
    for entry in data.get("streams", []):
        url = entry.get("url") or ""
        name = (entry.get("name") or "").replace("\n", " ")
        cached_marker = "[tb+]" in name.lower() or "⚡" in name
        if not url or (cached_only and not cached_marker):
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
            cached=True if cached_marker else None,
            **_stream_identity_fields(entry),
        ))
    return _apply_cache_evidence(streams, token, provider_asserted=bool(cached_only))


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


def debridio(addon_url, imdb_id, media_type, season=None, episode=None, token="", cached_only=True):
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
            **_stream_identity_fields(entry),
        ))

    streams = _apply_cache_evidence(streams, token, provider_asserted=False)
    return _cached_playable_only(streams) if cached_only else streams





def dedupe_streams(streams, profile=None):
    # Rank first so provider priority deterministically chooses which provider
    # survives when multiple providers expose the same release.
    ranked = rank_streams(streams, profile)
    unique = []
    seen = set()

    for stream in ranked:
        aliases = set(identity_aliases(stream))
        if aliases & seen:
            continue
        unique.append(stream)
        seen.update(aliases)

    return unique


def find_streams(
    token,
    enabled_providers,
    imdb_id,
    media_type,
    season=None,
    episode=None,
    profile=None,
    debridio_url="",
    cached_only=True,
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
        jobs.append(("comet", comet, (token, imdb_id, media_type, season, episode, cached_only)))
    if "torrentio" in enabled:
        jobs.append(("torrentio", torrentio, (token, imdb_id, media_type, season, episode, cached_only)))
    if "debridio" in enabled and debridio_url:
        jobs.append((
            "debridio",
            debridio,
            (debridio_url, imdb_id, media_type, season, episode, token, cached_only),
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

    results = dedupe_streams(results, profile)
    return _cached_playable_only(results) if cached_only else results
