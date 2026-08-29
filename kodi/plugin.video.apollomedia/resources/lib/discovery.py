from urllib.parse import quote
from functools import lru_cache

from .http import get_json


BASE_URL = "https://v3-cinemeta.strem.io"
TVMAZE_URL = "https://api.tvmaze.com"


def popular_movies():
    return get_json(f"{BASE_URL}/catalog/movie/top.json").get("metas", [])


def movie_catalog(catalog="top", genre="", skip=0):
    extras = []
    if genre:
        extras.append(f"genre={quote(str(genre))}")
    if int(skip or 0) > 0:
        extras.append(f"skip={int(skip)}")
    suffix = "/" + "&".join(extras) if extras else ""
    return get_json(f"{BASE_URL}/catalog/movie/{catalog}{suffix}.json").get("metas", [])


def search_movies(query):
    encoded = quote(query)
    return get_json(f"{BASE_URL}/catalog/movie/top/search={encoded}.json").get("metas", [])


def popular_series():
    return get_json(f"{BASE_URL}/catalog/series/top.json").get("metas", [])


def series_catalog(catalog="top", genre="", skip=0):
    extras = []
    if genre:
        extras.append(f"genre={quote(str(genre))}")
    if int(skip or 0) > 0:
        extras.append(f"skip={int(skip)}")
    suffix = "/" + "&".join(extras) if extras else ""
    return get_json(f"{BASE_URL}/catalog/series/{catalog}{suffix}.json").get("metas", [])


def search_series(query):
    encoded = quote(query)
    return get_json(f"{BASE_URL}/catalog/series/top/search={encoded}.json").get("metas", [])


@lru_cache(maxsize=128)
def series_details(imdb_id):
    return get_json(f"{BASE_URL}/meta/series/{imdb_id}.json").get("meta") or {}


@lru_cache(maxsize=128)
def movie_details(imdb_id):
    return get_json(f"{BASE_URL}/meta/movie/{imdb_id}.json").get("meta") or {}



@lru_cache(maxsize=128)
def tvmaze_episodes(imdb_id):
    """Return a season/episode map from TVMaze for exact IMDb series identity."""
    if not imdb_id:
        return {}
    try:
        show = get_json(f"{TVMAZE_URL}/lookup/shows?imdb={quote(str(imdb_id))}")
        show_id = int(show.get("id") or 0)
        if not show_id:
            return {}
        episodes = get_json(f"{TVMAZE_URL}/shows/{show_id}/episodes?specials=1")
    except Exception:
        return {}

    result = {}
    for item in episodes or []:
        season = int(item.get("season") or 0)
        number = int(item.get("number") or 0)
        if number <= 0:
            continue
        result[(season, number)] = item
    return result


def tvmaze_episode(imdb_id, season, episode):
    return tvmaze_episodes(imdb_id).get((int(season or 0), int(episode or 0)), {})

def progress_metadata(imdb_id, media_type, season=0, episode=0):
    if media_type == "movie":
        meta = movie_details(imdb_id)
        return {
            "title": meta.get("name") or meta.get("title") or "Unknown",
            "plot": meta.get("description") or "",
            "year": meta.get("releaseInfo") or meta.get("year"),
            "poster": meta.get("poster") or "",
            "fanart": meta.get("background") or "",
            "show_title": "",
        }
    meta = series_details(imdb_id)
    video = next((item for item in meta.get("videos", [])
                  if int(item.get("season") or 0) == int(season or 0)
                  and int(item.get("episode") or 0) == int(episode or 0)), {})

    show_title = meta.get("name") or meta.get("title") or ""
    title = video.get("name") or video.get("title") or ""

    # Cinemeta occasionally returns the show name as the episode title.
    # Use TVMaze only in that bad/generic case; its IMDb lookup keeps the
    # series identity exact and the full episode list is cached per show.
    generic = (
        not title
        or (show_title and str(title).strip().casefold() == str(show_title).strip().casefold())
    )
    maze = tvmaze_episode(imdb_id, season, episode) if generic else {}
    if maze.get("name"):
        title = maze["name"]

    return {
        "title": title or f"Episode {episode}",
        "plot": video.get("overview") or video.get("description") or meta.get("description") or "",
        "year": video.get("released") or meta.get("releaseInfo") or meta.get("year"),
        "poster": meta.get("poster") or video.get("thumbnail") or "",
        "fanart": meta.get("background") or "",
        "show_title": show_title,
    }
