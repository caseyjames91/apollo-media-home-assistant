import json
import os
import time
import uuid

import xbmcvfs

from .http import build_url, get_json, post_json


CACHE_SECONDS = 600
CLIENT_VERSION = "0.9.81"
DEVICE_ID_FILENAME = "jellyfin_device_id.txt"


def _device_id_path():
    directory = xbmcvfs.translatePath("special://profile/addon_data/plugin.video.apollomedia")
    os.makedirs(directory, exist_ok=True)
    return os.path.join(directory, DEVICE_ID_FILENAME)


def get_device_id():
    """Return a stable, unique Jellyfin device id for this Kodi profile."""
    path = _device_id_path()
    try:
        with open(path, "r", encoding="utf-8") as handle:
            value = handle.read().strip()
        if value:
            return value
    except Exception:
        pass

    value = "apollo-kodi-" + uuid.uuid4().hex
    tmp_path = path + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as handle:
            handle.write(value)
        os.replace(tmp_path, path)
    except Exception:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
        # Keep the current process usable even if profile storage is unavailable.
    return value


class JellyfinClient:
    def __init__(self, base_url, token="", user_id=""):
        self.base_url = (base_url or "").rstrip("/")
        self.token = (token or "").strip()
        self.user_id = (user_id or "").strip()

    @property
    def ready(self):
        return bool(self.base_url and self.token and self.user_id)

    def _authorization(self, include_token=True):
        parts = [
            'Client="Apollo Media"',
            'Device="Kodi"',
            f'DeviceId="{get_device_id()}"',
            f'Version="{CLIENT_VERSION}"',
        ]
        if self.user_id:
            parts.append(f'UserId="{self.user_id}"')
        if include_token and self.token:
            parts.append(f'Token="{self.token}"')
        return "MediaBrowser " + ", ".join(parts)

    def headers(self):
        authorization = self._authorization()
        return {
            "Authorization": authorization,
            "X-Emby-Authorization": authorization,
            "X-Emby-Token": self.token,
            "X-MediaBrowser-Token": self.token,
        }

    def authenticate(self, username, password):
        if not self.base_url:
            raise RuntimeError("Enter the Jellyfin server URL first")
        authorization = self._authorization(include_token=False)
        return post_json(
            build_url(self.base_url, "/Users/AuthenticateByName"),
            {"Username": username, "Pw": password},
            {"Authorization": authorization, "X-Emby-Authorization": authorization},
        )

    def server_info(self):
        return get_json(build_url(self.base_url, "/System/Info"), self.headers())

    def user(self):
        return get_json(build_url(self.base_url, f"/Users/{self.user_id}"), self.headers())

    def items(self, include_types="Movie", limit=5000, fields=None, enable_images=True,
              parent_id=None, sort_by="SortName", sort_order="Ascending", start_index=0):
        params = {
            "UserId": self.user_id,
            "Recursive": "true",
            "IncludeItemTypes": include_types,
            "Limit": limit,
            "StartIndex": max(0, int(start_index or 0)),
            "Fields": fields or "ProviderIds,Overview,RunTimeTicks,UserData,Path,ImageTags",
            "SortBy": sort_by,
            "SortOrder": sort_order,
            "EnableImages": "true" if enable_images else "false",
        }
        if parent_id:
            params["ParentId"] = parent_id
        data = get_json(build_url(self.base_url, "/Items", params), self.headers())
        return data.get("Items", [])

    def item(self, item_id):
        return get_json(
            build_url(self.base_url, f"/Users/{self.user_id}/Items/{item_id}"),
            self.headers(),
        )

    def resume_items(self, limit=50):
        params = {
            "UserId": self.user_id,
            "Limit": limit,
            "MediaTypes": "Video",
            "Fields": "ProviderIds,Overview,RunTimeTicks,UserData,SeriesId,SeriesName,SeasonId,ParentIndexNumber,IndexNumber,ProductionYear,DateCreated,PremiereDate",
            "EnableImages": "true",
        }
        data = get_json(build_url(self.base_url, "/UserItems/Resume", params), self.headers())
        return data.get("Items", [])

    def seasons(self, series_id):
        data = get_json(build_url(self.base_url, f"/Shows/{series_id}/Seasons", {
            "UserId": self.user_id,
            "Fields": "Overview,UserData,ImageTags,IndexNumber",
        }), self.headers())
        return data.get("Items", [])

    def episodes(self, series_id, season_id=None):
        params = {
            "UserId": self.user_id,
            "Fields": "Overview,RunTimeTicks,UserData,ProviderIds,ImageTags,Path,SeriesName,SeasonId,ParentIndexNumber,IndexNumber",
        }
        if season_id:
            params["SeasonId"] = season_id
        data = get_json(build_url(self.base_url, f"/Shows/{series_id}/Episodes", params), self.headers())
        return data.get("Items", [])

    def _cache_path(self, kind):
        directory = xbmcvfs.translatePath("special://profile/addon_data/plugin.video.apollomedia")
        os.makedirs(directory, exist_ok=True)
        return os.path.join(directory, f"jellyfin_{kind}_index.json")

    def library_index(self, kind, force=False):
        include_type = "Movie" if kind == "movie" else "Series"
        cache_path = self._cache_path(kind)
        if not force:
            try:
                with open(cache_path, "r", encoding="utf-8") as handle:
                    cached = json.load(handle)
                valid = (
                    cached.get("server") == self.base_url
                    and cached.get("user") == self.user_id
                    and time.time() - float(cached.get("created", 0)) < CACHE_SECONDS
                )
                if valid:
                    return cached.get("items", {})
            except Exception:
                pass

        index = {}
        for item in self.items(include_type, fields="ProviderIds", enable_images=False):
            provider_ids = item.get("ProviderIds") or {}
            imdb_id = str(provider_ids.get("Imdb") or provider_ids.get("IMDb") or "").lower()
            if imdb_id:
                index[imdb_id] = {"Id": item.get("Id"), "Name": item.get("Name")}
        try:
            with open(cache_path, "w", encoding="utf-8") as handle:
                json.dump({
                    "created": time.time(),
                    "server": self.base_url,
                    "user": self.user_id,
                    "items": index,
                }, handle)
        except Exception:
            pass
        return index

    def movie_index(self, force=False):
        return self.library_index("movie", force)

    def series_index(self, force=False):
        return self.library_index("series", force)

    def find_movie(self, imdb_id):
        return self.movie_index().get(str(imdb_id or "").strip().lower())

    def find_series(self, imdb_id):
        return self.series_index().get(str(imdb_id or "").strip().lower())

    def image_url(self, item_id, image_type="Primary", width=600):
        return build_url(
            self.base_url,
            f"/Items/{item_id}/Images/{image_type}",
            {"maxWidth": width, "quality": 90, "api_key": self.token},
        )

    def stream_url(self, item_id):
        play_session_id = uuid.uuid4().hex
        return build_url(self.base_url, f"/Videos/{item_id}/stream", {
            "api_key": self.token,
            "UserId": self.user_id,
            "DeviceId": get_device_id(),
            "PlaySessionId": play_session_id,
            "MediaSourceId": item_id,
            "Static": "true",
        })

    def set_resume(self, item_id, position_seconds):
        """
        Synchronize one resume position without fabricating a playback session.
        Existing watched/favorite/play-count user-data fields are preserved.
        """
        item = self.item(item_id) or {}
        user_data = dict(item.get("UserData") or {})
        user_data["PlaybackPositionTicks"] = max(
            0, int(float(position_seconds or 0) * 10000000)
        )
        return post_json(
            build_url(
                self.base_url,
                f"/Users/{self.user_id}/Items/{item_id}/UserData",
            ),
            user_data,
            self.headers(),
        )

    def clear_resume(self, item_id):
        """
        Clear only the user's resume position for one Jellyfin item.

        Preserve the rest of Jellyfin's user-data state, including played,
        favorite and play-count fields.
        """
        item = self.item(item_id) or {}
        user_data = dict(item.get("UserData") or {})
        user_data["PlaybackPositionTicks"] = 0
        return post_json(
            build_url(
                self.base_url,
                f"/Users/{self.user_id}/Items/{item_id}/UserData",
            ),
            user_data,
            self.headers(),
        )

    def report_playback(self, event, item_id, position_ticks, paused, play_session_id):
        endpoints = {
            "start": "/Sessions/Playing",
            "progress": "/Sessions/Playing/Progress",
            "stop": "/Sessions/Playing/Stopped",
        }
        payload = {
            "ItemId": item_id,
            "MediaSourceId": item_id,
            "PlaySessionId": play_session_id,
            "PositionTicks": max(0, int(position_ticks)),
            "IsPaused": bool(paused),
            "IsMuted": False,
            "CanSeek": True,
            "PlayMethod": "DirectStream",
            "RepeatMode": "RepeatNone",
            "EventName": {"start": "playbackstart", "progress": "timeupdate", "stop": "stop"}[event],
        }
        return post_json(build_url(self.base_url, endpoints[event]), payload, self.headers())
