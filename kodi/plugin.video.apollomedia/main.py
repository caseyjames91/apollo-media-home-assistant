import sys
import os
import re
import math
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlencode

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

from resources.lib.discovery import popular_movies, popular_series, search_movies, search_series, series_details, progress_metadata, movie_catalog, series_catalog
from resources.lib.compatibility import detect as detect_compatibility, profile as compatibility_profile
from resources.lib import progress, source_session, active_media, playback_session, ams
from resources.lib.jellyfin import JellyfinClient
from resources.lib.sources import find_streams
from resources.lib.torbox import link_account
from resources.lib.media_service import MediaService
from resources.lib.render.kodi import add_directory_item as render_media_item
from resources.lib.stream_dialog import StreamChooserDialog
from resources.lib.playback_intent import resolve_remote_position


ADDON = xbmcaddon.Addon()
HANDLE = int(sys.argv[1])
BASE_URL = sys.argv[0]


def parameters():
    return dict(parse_qsl(sys.argv[2][1:])) if len(sys.argv) > 2 and sys.argv[2] else {}


def plugin_url(**values):
    return BASE_URL + "?" + urlencode(values)


def jellyfin():
    return JellyfinClient(
        ADDON.getSettingString("jellyfin_url"),
        ADDON.getSettingString("jellyfin_token"),
        ADDON.getSettingString("jellyfin_user_id"),
    )


def media_service():
    return MediaService(jellyfin())


def notify(message, level=xbmcgui.NOTIFICATION_INFO):
    xbmcgui.Dialog().notification("Apollo Media", message, level, 5000)


def has_active_source_session():
    session = source_session.load()
    player = xbmc.Player()
    if not session or not player.isPlayingVideo():
        return False
    try:
        return player.getVideoInfoTag().getUniqueID("imdb") == session.get("imdb_id")
    except Exception:
        return False


def upcoming_badge(media):
    released = str(media.get("released") or "").strip()
    try:
        air_time = datetime.fromisoformat(released.replace("Z", "+00:00"))
        if air_time.tzinfo is None:
            air_time = air_time.replace(tzinfo=timezone.utc)
        if air_time > datetime.now(timezone.utc):
            return air_time.strftime("%b %d, %Y").upper().replace(" 0", " ")
    except ValueError:
        pass
    status = str(media.get("status") or "").strip().lower()
    if status in ("upcoming", "planned", "in production"):
        return "UPCOMING"
    release_info = str(media.get("releaseInfo") or media.get("year") or "").strip()
    if release_info.isdigit() and len(release_info) == 4 and int(release_info) > datetime.now().year:
        return "UPCOMING"
    return ""


def add_folder(label, action, **values):
    item = xbmcgui.ListItem(label=label)
    item.setProperty("IsPlayable", "false")
    xbmcplugin.addDirectoryItem(HANDLE, plugin_url(action=action, **values), item, True)


def add_action(label, action):
    item = xbmcgui.ListItem(label=label)
    item.setProperty("IsPlayable", "false")
    xbmcplugin.addDirectoryItem(HANDLE, plugin_url(action=action), item, False)


def literal_label(value):
    """Keep digit-leading media titles literal instead of Kodi localization IDs."""
    text = str(value or "")
    stripped = text.lstrip()
    if stripped and stripped[0].isdigit():
        return "\u200b" + text
    return text


def set_metadata(list_item, title, plot="", year=None, imdb_id="", poster="", fanart=""):
    tag = list_item.getVideoInfoTag()
    tag.setTitle(literal_label(title))
    if plot:
        tag.setPlot(plot)
    if year:
        try:
            tag.setYear(int(str(year)[:4]))
        except (TypeError, ValueError):
            pass
    if imdb_id:
        tag.setUniqueID(imdb_id, "imdb")
    artwork = {}
    if poster:
        artwork.update({"poster": poster, "thumb": poster})
    if fanart:
        artwork["fanart"] = fanart
    if artwork:
        list_item.setArt(artwork)


def _card_media_type(item_type, season=0, episode=0):
    value = str(item_type or "").strip().lower()
    if value in ("episode",):
        return "episode"
    if value in ("series", "show", "tvshow"):
        return "show"
    if value == "season":
        return "season"
    if int(episode or 0) > 0:
        return "episode"
    return "movie"


def _provider_id(item, *names):
    ids = item.get("ProviderIds") or {}
    for name in names:
        value = ids.get(name)
        if value:
            return str(value)
    return ""


def _card_route_fields(*, media_type, presentation_context="", imdb_id="", tmdb_id="",
                       jellyfin_item_id="", show_title="", season=0, episode=0,
                       release_date="", date_added="", last_episode_added="",
                       in_library=False, watched=False, show_target="", season_target="",
                       remove_target="", remote_auto_target="", remote_choose_target="",
                       card_play_target=""):
    values = {
        "apollo_media_type": _card_media_type(media_type, season, episode),
        "presentation_context": str(presentation_context or ""),
        "imdb": str(imdb_id or ""),
        "tmdb": str(tmdb_id or ""),
        "jellyfin_item_id": str(jellyfin_item_id or ""),
        "show_title": str(show_title or ""),
        "season": int(season or 0),
        "episode": int(episode or 0),
        "release_date": str(release_date or ""),
        "date_added": str(date_added or ""),
        "last_episode_added": str(last_episode_added or ""),
        "in_library": "1" if in_library else "0",
        "watched": "1" if watched else "0",
        "show_target": str(show_target or ""),
        "season_target": str(season_target or ""),
        "remove_target": str(remove_target or ""),
        "remote_auto_target": str(remote_auto_target or ""),
        "remote_choose_target": str(remote_choose_target or ""),
        "card_play_target": str(card_play_target or ""),
    }
    return values


def add_discovery_movie(movie, local=None, native_local=False, presentation_context="discovery"):
    imdb_id = movie.get("imdb_id") or movie.get("id") or ""
    title = movie.get("name") or movie.get("title") or "Unknown"
    label = title
    badge = upcoming_badge(movie)
    if badge:
        label += f"  [COLOR orange][{badge}][/COLOR]"
    if local:
        label += "  [COLOR gray]•[/COLOR]"
    item = xbmcgui.ListItem(label=label)
    set_metadata(
        item,
        title,
        movie.get("description") or "",
        movie.get("releaseInfo") or movie.get("year"),
        imdb_id,
        movie.get("poster") or "",
        movie.get("background") or "",
    )

    if local:
        position, duration = canonical_local_resume(
            imdb_id, "movie", 0, 0, title, local.get("Id") or ""
        )
    else:
        saved = progress.get(imdb_id, 0, 0) if imdb_id else None
        position = float((saved or {}).get("position") or 0)
        duration = float((saved or {}).get("duration") or 0)

    if position > 0 and duration > 0:
        item.getVideoInfoTag().setResumePoint(position, duration)

    item.setProperty("IsPlayable", "true")
    item.addContextMenuItems([(
        "Choose Remote Stream",
        f"RunPlugin({plugin_url(action='choose_external', imdb=imdb_id, media_type='movie', season=0, episode=0, title=title, resume_item_id=(local.get('Id') or '') if local else '')})",
    )])
    remote_auto_target, remote_choose_target = remote_card_targets(
        imdb_id, "movie", 0, 0, title, (local.get("Id") or "") if local else ""
    )
    route_fields = _card_route_fields(
        media_type="movie",
        presentation_context=presentation_context,
        imdb_id=imdb_id,
        tmdb_id=movie.get("tmdb_id") or movie.get("tmdb") or "",
        jellyfin_item_id=(local.get("Id") or "") if local else "",
        release_date=movie.get("released") or movie.get("releaseInfo") or "",
        in_library=bool(local),
        remote_auto_target=remote_auto_target,
        remote_choose_target=remote_choose_target,
    )
    target = (
        plugin_url(
            action="play_jellyfin_native",
            item_id=local.get("Id") or "",
            title=local.get("Name") or title,
            **route_fields,
        )
        if local and native_local
        else plugin_url(action="play_discovery", title=title, **route_fields)
    )
    xbmcplugin.addDirectoryItem(
        HANDLE,
        target,
        item,
        False,
    )


def latest_discovery_episode(imdb_id):
    """Return the newest already-released episode for headless show-row display."""
    if not imdb_id:
        return {}
    try:
        details = series_details(imdb_id) or {}
    except Exception:
        return {}

    now = datetime.now(timezone.utc)
    candidates = []
    for video in details.get("videos", []) or []:
        season = int(video.get("season") or 0)
        episode = int(video.get("episode") or 0)
        if season <= 0 or episode <= 0:
            continue
        released = str(video.get("released") or "").strip()
        if released:
            try:
                aired = datetime.fromisoformat(released.replace("Z", "+00:00"))
                if aired.tzinfo is None:
                    aired = aired.replace(tzinfo=timezone.utc)
                if aired > now:
                    continue
            except ValueError:
                pass
        title = str(video.get("name") or video.get("title") or "").strip()
        candidates.append((season, episode, title))

    if not candidates:
        return {}
    season, episode, title = max(candidates, key=lambda row: (row[0], row[1]))
    return {"season": season, "episode": episode, "title": title or f"Episode {episode}"}


def jellyfin_episode_hints(jf):
    """Build one latest-local-episode map in a single Jellyfin query."""
    hints = {}
    try:
        episodes = jf.items(
            "Episode",
            limit=5000,
            fields="SeriesId,SeriesName,ParentIndexNumber,IndexNumber,DateCreated,PremiereDate",
            enable_images=False,
        )
    except Exception:
        return hints

    for episode in episodes:
        series_id = str(episode.get("SeriesId") or "")
        season = int(episode.get("ParentIndexNumber") or 0)
        number = int(episode.get("IndexNumber") or 0)
        if not series_id or season <= 0 or number <= 0:
            continue
        candidate = {
            "season": season,
            "episode": number,
            "title": str(episode.get("Name") or f"Episode {number}").strip(),
            "date_added": str(episode.get("DateCreated") or ""),
            "release_date": str(episode.get("PremiereDate") or ""),
        }
        current = hints.get(series_id)
        candidate_added = str(candidate.get("date_added") or "")
        current_added = str((current or {}).get("date_added") or "")
        if not current or candidate_added > current_added or (
            candidate_added == current_added and (season, number) > (current["season"], current["episode"])
        ):
            hints[series_id] = candidate
    return hints


def episode_hint_params(hint):
    hint = hint or {}
    season = int(hint.get("season") or 0)
    episode = int(hint.get("episode") or 0)
    if season <= 0 or episode <= 0:
        return {}
    return {
        "latest_season": season,
        "latest_episode": episode,
        "latest_episode_title": str(hint.get("title") or f"Episode {episode}"),
    }


def jellyfin_series_indexes(jf):
    """Build parent-series lookup maps in one Jellyfin request."""
    by_id, by_name = {}, {}
    try:
        rows = jf.items(
            "Series",
            limit=5000,
            fields="ProviderIds,DateCreated,PremiereDate",
            enable_images=False,
        )
    except Exception:
        return by_id, by_name
    for row in rows:
        ids = row.get("ProviderIds") or {}
        imdb_id = str(ids.get("Imdb") or ids.get("IMDb") or "")
        entry = {
            "imdb": imdb_id,
            "tmdb": str(ids.get("Tmdb") or ids.get("TMDb") or ""),
            "id": str(row.get("Id") or ""),
            "name": str(row.get("Name") or ""),
            "date_added": str(row.get("DateCreated") or ""),
            "release_date": str(row.get("PremiereDate") or ""),
        }
        if entry["id"]:
            by_id[entry["id"]] = entry
        if entry["name"]:
            by_name[entry["name"].strip().casefold()] = entry
    return by_id, by_name


def _annotate_episode_parent_identity(video, by_id, by_name):
    series_id = str(video.get("SeriesId") or "")
    parent = by_id.get(series_id) or by_name.get(str(video.get("SeriesName") or "").strip().casefold()) or {}
    if parent.get("imdb"):
        video["_ApolloSeriesImdb"] = parent["imdb"]
    if parent.get("tmdb"):
        video["_ApolloSeriesTmdb"] = parent["tmdb"]
    if parent.get("id"):
        video["_ApolloSeriesId"] = parent["id"]
    return video


def add_discovery_series(series, local=None, native_local=False, episode_hint=None, presentation_context="discovery"):
    imdb_id = series.get("imdb_id") or series.get("id") or ""
    title = series.get("name") or series.get("title") or "Unknown"
    label = title
    badge = upcoming_badge(series)
    if badge:
        label += f"  [COLOR orange][{badge}][/COLOR]"
    if local:
        label += "  [COLOR gray]•[/COLOR]"
    item = xbmcgui.ListItem(label=literal_label(label))
    set_metadata(
        item,
        title,
        series.get("description") or "",
        series.get("releaseInfo") or series.get("year"),
        imdb_id,
        series.get("poster") or "",
        series.get("background") or "",
    )
    item.setProperty("IsPlayable", "false")
    xbmcplugin.addDirectoryItem(
        HANDLE,
        plugin_url(
            action="discovery_seasons",
            title=title,
            native_local="1" if native_local else "",
            **_card_route_fields(
                media_type="show",
                presentation_context=presentation_context,
                imdb_id=imdb_id,
                tmdb_id=series.get("tmdb_id") or series.get("tmdb") or "",
                jellyfin_item_id=(local.get("Id") or "") if local else "",
                release_date=series.get("released") or series.get("releaseInfo") or "",
                in_library=bool(local),
            ),
        ),
        item,
        True,
    )


def add_discovery_season(imdb_id, season_number, title, local=False, native_local=False):
    label = "Specials" if season_number == 0 else f"Season {season_number}"
    if local:
        label += "  [COLOR gray]•[/COLOR]"
    item = xbmcgui.ListItem(label=label)
    item.getVideoInfoTag().setTitle(literal_label(label))
    item.getVideoInfoTag().setSeason(season_number)
    show_art = public_art(imdb_id)
    if show_art:
        item.setArt({"poster": show_art, "thumb": show_art})
    item.setProperty("IsPlayable", "false")
    xbmcplugin.addDirectoryItem(
        HANDLE,
        plugin_url(
            action="discovery_episodes",
            imdb=imdb_id,
            season=season_number,
            title=title,
            native_local="1" if native_local else "",
            apollo_media_type="season",
            presentation_context="browse",
            in_library="1" if local else "0",
            show_title=title,
            show_target=plugin_url(
                action="discovery_seasons", imdb=imdb_id, title=title,
                native_local="1" if native_local else "",
            ),
        ),
        item,
        True,
    )


def add_discovery_episode(episode, imdb_id, local=None, native_local=False):
    season_number = int(episode.get("season") or 0)
    episode_number = int(episode.get("episode") or 0)
    title = episode.get("name") or episode.get("title") or f"Episode {episode_number}"
    label = f"{episode_number}. {title}"
    badge = upcoming_badge(episode)
    if badge:
        label += f"  [COLOR orange][{badge}][/COLOR]"
    if local:
        label += "  [COLOR gray]•[/COLOR]"
    item = xbmcgui.ListItem(label=label)
    set_metadata(
        item,
        title,
        episode.get("overview") or episode.get("description") or "",
        poster=episode.get("thumbnail") or public_art(imdb_id),
    )
    tag = item.getVideoInfoTag()
    tag.setSeason(season_number)
    tag.setEpisode(episode_number)
    if local:
        position, duration = canonical_local_resume(
            imdb_id, "series", season_number, episode_number, title,
            local.get("Id") or "",
        )
        if position > 0 and duration > 0:
            tag.setResumePoint(position, duration)
        item.setArt({"thumb": jellyfin().image_url(local.get("Id") or "")})
        item.setProperty("IsPlayable", "true")
        target = plugin_url(
            action="play_jellyfin_native" if native_local else "play_jellyfin",
            item_id=local.get("Id") or "",
            title=local.get("Name") or title,
            apollo_media_type="episode", presentation_context="browse",
            imdb=imdb_id, jellyfin_item_id=local.get("Id") or "",
            show_title=episode.get("showTitle") or episode.get("seriesName") or "",
            season=season_number, episode=episode_number, in_library="1",
            show_target=plugin_url(action="discovery_seasons", imdb=imdb_id, title=episode.get("showTitle") or ""),
            season_target=plugin_url(action="discovery_episodes", imdb=imdb_id, season=season_number),
            remote_auto_target=remote_card_targets(
                imdb_id, "series", season_number, episode_number, title,
                (local.get("Id") or "") if local else ""
            )[0],
            remote_choose_target=remote_card_targets(
                imdb_id, "series", season_number, episode_number, title,
                (local.get("Id") or "") if local else ""
            )[1],
            card_play_target=plugin_url(
                action="play_resolved",
                source="jellyfin",
                item_id=local.get("Id") or "",
                title=local.get("Name") or title,
            ),
        )
    else:
        saved = progress.get(imdb_id, season_number, episode_number)
        if saved:
            position = float(saved.get("position") or 0)
            duration = float(saved.get("duration") or 0)
            if position > 0 and duration > 0:
                tag.setResumePoint(position, duration)

        item.setProperty("IsPlayable", "true")
        target = plugin_url(
            action="play_resolved",
            source="ams",
            imdb=imdb_id,
            media_type="series",
            apollo_media_type="episode", presentation_context="browse",
            season=season_number,
            episode=episode_number,
            title=title, in_library="0",
            show_target=plugin_url(action="discovery_seasons", imdb=imdb_id, title=episode.get("showTitle") or ""),
            season_target=plugin_url(action="discovery_episodes", imdb=imdb_id, season=season_number),
            remote_auto_target=remote_card_targets(
                imdb_id, "series", season_number, episode_number, title, ""
            )[0],
            remote_choose_target=remote_card_targets(
                imdb_id, "series", season_number, episode_number, title, ""
            )[1],
        )
    if local:
        item.addContextMenuItems([
            (
                "Play from Stream",
                f"RunPlugin({plugin_url(action='play_external_prompt', imdb=imdb_id, media_type='series', season=season_number, episode=episode_number, title=title, resume_item_id=(local.get('Id') or '') if local else '')})",
            ),
            (
                "Choose Remote Stream",
                f"RunPlugin({plugin_url(action='choose_external', imdb=imdb_id, media_type='series', season=season_number, episode=episode_number, title=title, resume_item_id=(local.get('Id') or '') if local else '')})",
            ),
        ])
    else:
        item.addContextMenuItems([(
            "Choose Remote Stream",
            f"RunPlugin({plugin_url(action='choose_external', imdb=imdb_id, media_type='series', season=season_number, episode=episode_number, title=title, resume_item_id='')})",
        )])
    xbmcplugin.addDirectoryItem(HANDLE, target, item, False)


def add_jellyfin_movie(movie, continue_item=False):
    jf = jellyfin()
    item_id = movie.get("Id") or ""
    title = movie.get("Name") or "Unknown"
    provider_ids = movie.get("ProviderIds") or {}
    imdb_id = provider_ids.get("Imdb") or provider_ids.get("IMDb") or ""
    item = xbmcgui.ListItem(label=title)
    set_metadata(
        item,
        title,
        movie.get("Overview") or "",
        movie.get("ProductionYear"),
        imdb_id,
        jf.image_url(item_id),
        jf.image_url(item_id, "Backdrop", 1280),
    )
    position, duration = canonical_local_resume(
        imdb_id, "movie", 0, 0, title, item_id
    )
    if position > 0 and duration > 0:
        item.getVideoInfoTag().setResumePoint(position, duration)
    item.setProperty("IsPlayable", "true")
    if imdb_id:
        item.addContextMenuItems([
            (
                "Play from Stream",
                f"RunPlugin({plugin_url(action='play_external_prompt', imdb=imdb_id, media_type='movie', season=0, episode=0, title=title, resume_item_id=item_id)})",
            ),
            (
                "Choose Remote Stream",
                f"RunPlugin({plugin_url(action='choose_external', imdb=imdb_id, media_type='movie', season=0, episode=0, title=title, resume_item_id=item_id)})",
            ),
        ])
    if continue_item:
        item.addContextMenuItems([(
            "Remove from Continue Watching",
            f"RunPlugin({plugin_url(action='remove_continue', source='jellyfin', item_id=item_id, imdb=imdb_id, season=0, episode=0)})",
        )])
    xbmcplugin.addDirectoryItem(
        HANDLE,
        plugin_url(action="play_jellyfin", item_id=item_id, title=title),
        item,
        False,
    )


def jellyfin_series_display(series):
    """Return display metadata for a local Jellyfin series without slowing the library."""
    provider_ids = series.get("ProviderIds") or {}
    imdb_id = provider_ids.get("Imdb") or provider_ids.get("IMDb") or ""

    jellyfin_title = str(series.get("Name") or "").strip()
    bad_names = {"tvshows", "tvshow", "shows", "series", "unknown"}

    raw_path = str(series.get("Path") or "").rstrip("/\\")
    path_title = os.path.basename(raw_path) if raw_path else ""

    # Normal Jellyfin titles are already useful. Do not make a network
    # metadata request for every show just to redraw the library.
    if jellyfin_title and jellyfin_title.casefold() not in bad_names:
        return {
            "title": jellyfin_title,
            "plot": series.get("Overview") or "",
            "year": series.get("ProductionYear"),
            "imdb_id": imdb_id,
        }

    # Only repair metadata when Jellyfin is clearly broken.
    canonical = {}
    if imdb_id:
        try:
            canonical = series_details(imdb_id) or {}
        except Exception as exc:
            xbmc.log(
                f"[Apollo Media] Series metadata repair failed for {imdb_id}: {exc}",
                xbmc.LOGWARNING,
            )

    title = (
        canonical.get("name")
        or canonical.get("title")
        or path_title
        or jellyfin_title
        or "Unknown"
    )

    return {
        "title": title,
        "plot": canonical.get("description") or series.get("Overview") or "",
        "year": canonical.get("releaseInfo") or canonical.get("year") or series.get("ProductionYear"),
        "imdb_id": imdb_id,
    }


def add_jellyfin_series(series, display=None):
    jf = jellyfin()
    item_id = series.get("Id") or ""
    display = display or jellyfin_series_display(series)
    title = display["title"]
    imdb_id = display["imdb_id"]

    item = xbmcgui.ListItem(label=literal_label(title))
    set_metadata(
        item,
        title,
        display["plot"],
        display["year"],
        imdb_id,
        jf.image_url(item_id),
        jf.image_url(item_id, "Backdrop", 1280),
    )
    item.setProperty("IsPlayable", "false")
    xbmcplugin.addDirectoryItem(
        HANDLE,
        plugin_url(
            action="seasons", series_id=item_id, title=title, imdb=imdb_id,
            apollo_media_type="show", presentation_context="library",
            jellyfin_item_id=item_id, in_library="1",
        ),
        item,
        True,
    )


def add_season(season, series_id, imdb_id=""):
    jf = jellyfin()
    season_id = season.get("Id") or ""
    title = season.get("Name") or "Season"
    item = xbmcgui.ListItem(label=title)
    season_art = jellyfin_primary_art(jf, season)
    show_art = public_art(imdb_id)
    set_metadata(
        item,
        title,
        season.get("Overview") or "",
        imdb_id=imdb_id,
        poster=season_art or show_art,
    )
    item.setProperty("IsPlayable", "false")
    xbmcplugin.addDirectoryItem(
        HANDLE,
        plugin_url(
            action="episodes", series_id=series_id, season_id=season_id, imdb=imdb_id,
            apollo_media_type="season", presentation_context="browse",
            jellyfin_item_id=season_id, season=int(season.get("IndexNumber") or 0), in_library="1",
        ),
        item,
        True,
    )


def add_episode(episode, imdb_id="", force_series_art=False, continue_label=False):
    jf = jellyfin()
    item_id = episode.get("Id") or ""
    number = episode.get("IndexNumber")
    season_number = int(episode.get("ParentIndexNumber") or 0)

    canonical = {}
    if imdb_id and number is not None:
        try:
            canonical = progress_metadata(
                imdb_id,
                "series",
                season_number,
                int(number),
            )
        except Exception as exc:
            xbmc.log(
                f"[Apollo Media] Episode metadata lookup failed: {exc}",
                xbmc.LOGWARNING,
            )

    title = best_episode_title(episode, canonical, season_number, number)
    plot = canonical.get("plot") or episode.get("Overview") or ""
    show_title = (
        episode.get("SeriesName")
        or canonical.get("show_title")
        or ""
    )

    if continue_label and number is not None:
        code = f"S{season_number:02d}E{int(number):02d}"
        label = f"{show_title} • {code} • {title}" if show_title else f"{code} • {title}"
    else:
        label = f"{number}. {title}" if number is not None else title

    item = xbmcgui.ListItem(label=literal_label(label))

    show_art = public_art(imdb_id)
    episode_art = jellyfin_primary_art(jf, episode)
    set_metadata(
        item,
        title,
        plot,
        imdb_id=imdb_id,
        poster=show_art if force_series_art else (episode_art or show_art),
    )

    tag = item.getVideoInfoTag()
    if number is not None:
        tag.setEpisode(int(number))
    if episode.get("ParentIndexNumber") is not None:
        tag.setSeason(season_number)
    if show_title:
        tag.setTvShowTitle(show_title)

    position, duration = canonical_local_resume(
        imdb_id, "series", season_number, int(number or 0), title, item_id
    )
    if position > 0 and duration > 0:
        tag.setResumePoint(position, duration)

    item.setProperty("IsPlayable", "true")
    if imdb_id and number is not None:
        item.addContextMenuItems([
            (
                "Play from Stream",
                f"RunPlugin({plugin_url(action='play_external_prompt', imdb=imdb_id, media_type='series', season=season_number, episode=int(number), title=title, resume_item_id=item_id)})",
            ),
            (
                "Choose Remote Stream",
                f"RunPlugin({plugin_url(action='choose_external', imdb=imdb_id, media_type='series', season=season_number, episode=int(number), title=title, resume_item_id=item_id)})",
            ),
        ])
    if continue_label:
        item.addContextMenuItems([(
            "Remove from Continue Watching",
            f"RunPlugin({plugin_url(action='remove_continue', source='jellyfin', item_id=item_id, imdb=imdb_id, season=season_number, episode=int(number or 0))})",
        )])
    xbmcplugin.addDirectoryItem(
        HANDLE,
        plugin_url(
            action="play_jellyfin", item_id=item_id, title=title,
            apollo_media_type="episode", presentation_context="browse",
            imdb=imdb_id, jellyfin_item_id=item_id, show_title=show_title,
            season=season_number, episode=int(number or 0), in_library="1",
            show_target=plugin_url(action="discovery_seasons", imdb=imdb_id, title=show_title) if imdb_id else "",
            season_target=plugin_url(action="discovery_episodes", imdb=imdb_id, season=season_number) if imdb_id else "",
        ),
        item,
        False,
    )


def require_jellyfin():
    jf = jellyfin()
    if jf.ready:
        return jf
    notify("Connect your Jellyfin user first", xbmcgui.NOTIFICATION_WARNING)
    return None


def home():
    jf = jellyfin()

    # AMS-owned Continue Watching and Apollo discovery remain usable without
    # a Jellyfin connection.
    add_folder("Continue Watching", "continue")

    if jf.ready:
        add_folder("Trending Movies", "trending")
        add_folder("Trending Shows", "trending_series")
        add_folder("Popular Movies", "popular")
        add_folder("Popular Shows", "popular_series")
        add_folder("Library Movies", "library")
        add_folder("Library Shows", "series_library")

    add_folder("Search Movies", "search")
    add_folder("Search Shows", "search_series")

    if jf.ready:
        add_action("Reconnect Jellyfin User", "connect_jellyfin")
    else:
        add_action("Connect Jellyfin User", "connect_jellyfin")

    if ADDON.getSettingString("torbox_token"):
        add_action("Relink TorBox", "link_torbox")
    else:
        add_action("Link TorBox", "link_torbox")

    add_action("Detect Device Compatibility", "detect_compatibility")

    if has_active_source_session():
        add_action("Current Stream Info", "current_stream_info")
        add_action("Try Next Stream", "try_next")
        add_action("Flag Current Stream", "flag_current")

    add_action("Settings", "settings")
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)

def connect_jellyfin():
    server_url = ADDON.getSettingString("jellyfin_url")
    if not server_url:
        ADDON.openSettings()
        server_url = ADDON.getSettingString("jellyfin_url")
    if not server_url:
        notify("A Jellyfin server URL is required", xbmcgui.NOTIFICATION_WARNING)
        finish_action()
        return
    username = xbmcgui.Dialog().input("Jellyfin username")
    if not username:
        finish_action()
        return
    password = xbmcgui.Dialog().input(
        "Jellyfin password",
        type=xbmcgui.INPUT_ALPHANUM,
        option=xbmcgui.ALPHANUM_HIDE_INPUT,
    )
    try:
        result = JellyfinClient(server_url).authenticate(username, password)
        user = result.get("User") or {}
        token = result.get("AccessToken") or ""
        user_id = user.get("Id") or ""
        if not token or not user_id:
            raise RuntimeError("Jellyfin did not return a user session")
        ADDON.setSettingString("jellyfin_token", token)
        ADDON.setSettingString("jellyfin_user_id", user_id)
        notify(f"Connected as {user.get('Name') or username}")
    except Exception as exc:
        xbmcgui.Dialog().ok("Apollo Media - login failed", str(exc))
    finish_action()


def finish_action():
    xbmcplugin.endOfDirectory(HANDLE, succeeded=False, cacheToDisc=False)
    xbmc.executebuiltin(f"Container.Update({BASE_URL},replace)")



def render_movie_media(media):
    if media.in_library and media.ids.jellyfin:
        # Local discovery rows use canonical Apollo/Jellyfin progress.
        position, duration = canonical_local_resume(
            media.ids.imdb,
            "movie",
            0,
            0,
            media.title,
            media.ids.jellyfin,
        )
        media.resume.position = float(position or 0)
        media.resume.duration = float(duration or 0)
    elif media.ids.imdb:
        # Remote-only discovery rows use Apollo's identity progress ledger.
        saved = progress.get(media.ids.imdb, 0, 0)
        if saved:
            media.resume.position = float(saved.get("position") or 0)
            media.resume.duration = float(saved.get("duration") or 0)

    if media.ids.imdb:
        # Manual source selection is useful for both local and non-local items.
        media.playback["remote_choose_url"] = plugin_url(
            action="choose_external",
            imdb=media.ids.imdb,
            media_type="movie",
            season=0,
            episode=0,
            title=media.title,
            resume_item_id=media.ids.jellyfin or "",
        )

    if media.in_library and media.ids.imdb:
        # Local items additionally expose Play from Stream because normal click
        # still prefers Jellyfin.
        media.playback["remote_auto_url"] = plugin_url(
            action="play_external_prompt",
            imdb=media.ids.imdb,
            media_type="movie",
            season=0,
            episode=0,
            title=media.title,
            resume_item_id=media.ids.jellyfin or "",
        )
    if media.local and media.ids.jellyfin:
        target = plugin_url(
            action="play_jellyfin",
            item_id=media.ids.jellyfin,
            title=media.title,
        )
    else:
        target = plugin_url(
            action="play_discovery",
            imdb=media.ids.imdb,
            title=media.title,
        )
    render_media_item(HANDLE, target, media, False)


def render_show_media(media):
    if media.source == "jellyfin" and media.ids.jellyfin:
        target = plugin_url(
            action="seasons",
            series_id=media.ids.jellyfin,
            title=media.title,
            imdb=media.ids.imdb,
        )
    else:
        target = plugin_url(
            action="discovery_seasons",
            imdb=media.ids.imdb,
            title=media.title,
        )
    render_media_item(HANDLE, target, media, True)


def trending():
    jf = require_jellyfin()
    xbmcplugin.setContent(HANDLE, "movies")
    if jf:
        try:
            for media in media_service().trending_movies():
                render_movie_media(media)
        except Exception as exc:
            notify(f"Could not load trending movies: {exc}", xbmcgui.NOTIFICATION_ERROR)
    xbmcplugin.endOfDirectory(HANDLE)


def trending_tv():
    jf = require_jellyfin()
    xbmcplugin.setContent(HANDLE, "tvshows")
    if jf:
        try:
            for media in media_service().trending_shows():
                render_show_media(media)
        except Exception as exc:
            notify(f"Could not load trending shows: {exc}", xbmcgui.NOTIFICATION_ERROR)
    xbmcplugin.endOfDirectory(HANDLE)


def popular():
    jf = require_jellyfin()
    xbmcplugin.setContent(HANDLE, "movies")
    if jf:
        try:
            for media in media_service().popular_movies():
                render_movie_media(media)
        except Exception as exc:
            notify(f"Could not load movies: {exc}", xbmcgui.NOTIFICATION_ERROR)
    xbmcplugin.endOfDirectory(HANDLE)

def search():
    query = xbmcgui.Dialog().input("Search movies")
    xbmcplugin.setContent(HANDLE, "movies")
    if query:
        try:
            for movie in search_movies(query):
                add_discovery_movie(
                    movie,
                    local=None,
                    native_local=False,
                    presentation_context="search",
                )
        except Exception as exc:
            notify(f"Search failed: {exc}", xbmcgui.NOTIFICATION_ERROR)
    xbmcplugin.endOfDirectory(HANDLE)

def remote_movie_catalog(list_type="popular", query=""):
    """Headless movie listing for Kodi JSON-RPC/Home Assistant clients."""
    if list_type == "library":
        library()
        return
    jf = require_jellyfin()
    xbmcplugin.setContent(HANDLE, "movies")
    if jf:
        try:
            local_index = jf.movie_index()
            if query:
                movies = search_movies(query)
            elif list_type == "new":
                movies = movie_catalog("year", str(datetime.now().year))
            elif list_type == "featured":
                movies = movie_catalog("imdbRating")
            else:
                movies = popular_movies()
            for movie in movies:
                imdb_id = str(movie.get("imdb_id") or movie.get("id") or "").lower()
                add_discovery_movie(
                    movie, local_index.get(imdb_id), native_local=True,
                    presentation_context="popular" if list_type == "popular" else list_type,
                )
        except Exception as exc:
            notify(f"Could not load movies: {exc}", xbmcgui.NOTIFICATION_ERROR)
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)


def remote_empty_feed(content="movies"):
    xbmcplugin.setContent(HANDLE, content)
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)


def remote_recently_released_episodes():
    jf = require_jellyfin()
    xbmcplugin.setContent(HANDLE, "episodes")
    if jf:
        try:
            by_id, by_name = jellyfin_series_indexes(jf)
            rows = jf.items(
                "Episode", limit=60,
                fields="ProviderIds,Overview,RunTimeTicks,UserData,SeriesId,SeriesName,SeasonId,ParentIndexNumber,IndexNumber,DateCreated,PremiereDate,ImageTags",
                sort_by="PremiereDate", sort_order="Descending",
            )
            for row in rows:
                _annotate_episode_parent_identity(row, by_id, by_name)
                add_remote_jellyfin_item(row, card_playback=True, presentation_context="recently_released")
        except Exception as exc:
            notify(f"Could not load recently released episodes: {exc}", xbmcgui.NOTIFICATION_ERROR)
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)


def remote_recently_added_shows():
    remote_jellyfin_library("Series", sort_by="DateCreated", sort_order="Descending", limit=60, presentation_context="recently_added")


def remote_recently_released_movies():
    remote_jellyfin_library("Movie", sort_by="PremiereDate", sort_order="Descending", limit=60, presentation_context="recently_released")


def remote_recently_added_movies():
    remote_jellyfin_library("Movie", sort_by="DateCreated", sort_order="Descending", limit=60, presentation_context="recently_added")


def remote_media_list(list_type="popular", query="", offset=0, limit=60, sort_by="SortName", sort_order="Ascending"):
    if list_type == "continue":
        remote_continue_watching()
    elif list_type == "active":
        remote_active_playback()
    elif list_type == "up_next":
        # Intentionally empty until Trakt (or another reliable watched-history source) is available.
        remote_empty_feed("episodes")
    elif list_type == "library_movies":
        remote_jellyfin_library("Movie", sort_by=sort_by, sort_order=sort_order,
                                 limit=limit, start_index=offset, presentation_context="library")
    elif list_type == "library_shows":
        remote_jellyfin_library("Series", sort_by=sort_by, sort_order=sort_order,
                                 limit=limit, start_index=offset, presentation_context="library")
    elif list_type == "recently_released_episodes":
        remote_recently_released_episodes()
    elif list_type == "recently_added_shows":
        remote_recently_added_shows()
    elif list_type == "recently_released_movies":
        remote_recently_released_movies()
    elif list_type == "recently_added_movies":
        remote_recently_added_movies()
    elif list_type == "popular_shows":
        remote_series_catalog("popular_shows")
    elif list_type == "popular_movies":
        remote_movie_catalog("popular", query)
    elif list_type in ("trending_shows", "trending_movies"):
        # Cinemeta exposes Popular, New and Featured but no true Trending catalog.
        # Keep these canonical rows intentionally empty until Trakt is integrated.
        remote_empty_feed("tvshows" if list_type.endswith("shows") else "movies")
    else:
        remote_empty_feed("movies")


def current_player_technical_info():
    """Best-effort actual player stream metadata for both local and remote playback."""
    try:
        active = json.loads(xbmc.executeJSONRPC(json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "Player.GetActivePlayers",
        }))).get("result") or []
        video_player = next((row for row in active if row.get("type") == "video"), None)
        if not video_player:
            return {}

        result = json.loads(xbmc.executeJSONRPC(json.dumps({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "Player.GetProperties",
            "params": {
                "playerid": int(video_player.get("playerid")),
                "properties": ["currentvideostream", "currentaudiostream"],
            },
        }))).get("result") or {}

        video = result.get("currentvideostream") or {}
        audio = result.get("currentaudiostream") or {}

        height = int(video.get("height") or 0)
        width = int(video.get("width") or 0)
        if height >= 2000 or width >= 3800:
            quality = "4K / 2160p"
        elif height >= 1000 or width >= 1900:
            quality = "1080p"
        elif height >= 700 or width >= 1200:
            quality = "720p"
        elif height > 0:
            quality = f"{height}p"
        else:
            quality = ""

        video_bits = [quality] if quality else []
        codec = str(video.get("codec") or "").upper()
        codec_alias = {
            "HEVC": "HEVC", "H265": "HEVC", "H.265": "HEVC",
            "H264": "H.264", "H.264": "H.264", "AVC": "H.264",
            "AV1": "AV1",
        }.get(codec, codec)
        if codec_alias:
            video_bits.append(codec_alias)
        hdr = str(video.get("hdrtype") or "").strip().upper()
        if hdr:
            video_bits.append(hdr.replace("DOLBYVISION", "Dolby Vision"))

        audio_codec = str(audio.get("codec") or "").strip().upper()
        audio_alias = {
            "EAC3": "Dolby Digital Plus",
            "AC3": "Dolby Digital",
            "TRUEHD": "TrueHD",
            "DTSHD_MA": "DTS-HD MA",
            "DTSHD_HRA": "DTS-HD",
            "DTS": "DTS",
            "AAC": "AAC",
        }.get(audio_codec, audio_codec)
        channels = audio.get("channels")
        audio_bits = [audio_alias] if audio_alias else []
        if channels not in (None, ""):
            try:
                numeric = float(channels)
                if numeric >= 6:
                    audio_bits.append("5.1+" if numeric != 8 else "7.1")
                elif numeric >= 2:
                    audio_bits.append("2.0")
            except Exception:
                pass

        return {
            "quality": quality,
            "video": " · ".join(bit for bit in video_bits if bit),
            "audio": " · ".join(bit for bit in audio_bits if bit),
        }
    except Exception:
        return {}


def remote_active_playback():
    """Expose safe active Apollo identity only when Kodi is playing this session."""
    session = source_session.load() or {}
    selected = source_session.current() or {}
    local = active_media.load()
    try:
        player = xbmc.Player()
        if not player.isPlayingVideo():
            xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)
            return
        remote = bool(selected and player.getPlayingFile() == selected.get("url"))
        local_id = player.getVideoInfoTag().getUniqueID("jellyfin")
        is_local = bool(local and local.get("source") == "local" and local_id and local_id == local.get("jellyfin_item_id"))
        if not remote and not is_local:
            xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)
            return
    except Exception:
        xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)
        return
    data = session if remote else local
    imdb_id = str(data.get("imdb_id") or "")
    media_type = str(data.get("media_type") or "movie")
    season = int(data.get("season") or 0)
    episode = int(data.get("episode") or 0)
    metadata = progress_metadata(imdb_id, media_type, season, episode) or {}
    card_media_type = "episode" if episode > 0 else "movie"
    title = metadata.get("title") or data.get("title") or "Unknown"
    show_title = metadata.get("show_title") or data.get("show_title") or ""
    show_target = plugin_url(action="discovery_seasons", imdb=imdb_id, title=show_title) if show_title and imdb_id else ""
    season_target = plugin_url(action="discovery_episodes", imdb=imdb_id, season=season) if show_title and imdb_id and season else ""
    identity = continue_key(imdb_id, season, episode, data.get("jellyfin_item_id") or "")
    item = xbmcgui.ListItem(label=title)
    set_metadata(item, title, metadata.get("plot") or "", metadata.get("year"), imdb_id,
                 metadata.get("poster") or "", metadata.get("fanart") or "")
    tag = item.getVideoInfoTag()
    if episode:
        tag.setSeason(season); tag.setEpisode(episode)
        if show_title: tag.setTvShowTitle(show_title)
    remote_auto_target, remote_choose_target = remote_card_targets(
        imdb_id, media_type, season, episode, title, data.get("jellyfin_item_id") or ""
    )
    current_stream = selected if remote else {}
    current_index = int(session.get("index") or 0) if remote else -1
    stream_count = len(session.get("streams") or []) if remote else 0
    provider = str(current_stream.get("provider") or "") if remote else ""
    current_flag = source_session.flag_for_url(current_stream.get("url") or "") if remote else None
    player_technical = current_player_technical_info()
    quality = str(player_technical.get("quality") or current_stream.get("quality") or "")
    video_info = str(player_technical.get("video") or current_stream.get("video") or "")
    audio_info = str(player_technical.get("audio") or current_stream.get("audio") or "")
    jellyfin_item_id = str(data.get("jellyfin_item_id") or "")
    local_target = plugin_url(
        action="remote_play_jellyfin",
        item_id=jellyfin_item_id,
        title=title,
    ) if jellyfin_item_id else ""

    xbmcplugin.addDirectoryItem(HANDLE, plugin_url(
        action="apollo_active_media", apollo_identity=identity, apollo_remote="1" if remote else "0",
        imdb=imdb_id, media_type=media_type, apollo_media_type=card_media_type, season=season, episode=episode,
        jellyfin_item_id=data.get("jellyfin_item_id") or "",
        show_title=show_title, title=title, show_target=show_target,
        season_target=season_target,
        remote_auto_target=remote_auto_target,
        remote_choose_target=remote_choose_target,
        apollo_provider=provider,
        apollo_stream_index=current_index,
        apollo_stream_count=stream_count,
        apollo_stream_flagged="1" if current_flag else "0",
        apollo_local_target=local_target,
        apollo_quality=quality,
        apollo_video_info=video_info,
        apollo_audio_info=audio_info), item, False)
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)


def remote_series_catalog(list_type="popular_shows"):
    """Headless show listing. Cinemeta top.json is its explicit Popular catalog."""
    jf = require_jellyfin()
    xbmcplugin.setContent(HANDLE, "tvshows")
    if jf:
        try:
            local_index = jf.series_index()
            shows = popular_series() if list_type == "popular_shows" else []
            for series in shows:
                imdb_id = str(series.get("imdb_id") or series.get("id") or "").lower()
                add_discovery_series(
                    series,
                    local_index.get(imdb_id),
                    native_local=True,
                    episode_hint=None,
                    presentation_context="popular",
                )
        except Exception as exc:
            notify(f"Could not load TV list: {exc}", xbmcgui.NOTIFICATION_ERROR)
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)


def public_art(imdb_id, image_type="poster"):
    if not imdb_id:
        return ""
    size = "medium" if image_type == "poster" else "medium"
    return f"https://images.metahub.space/{image_type}/{size}/{imdb_id}/img"


def jellyfin_primary_art(jf, item):
    """Return Jellyfin primary artwork only when the item advertises one."""
    image_tags = item.get("ImageTags") or {}
    if image_tags.get("Primary") or item.get("PrimaryImageTag"):
        return jf.image_url(item.get("Id") or "")
    return ""


def clean_episode_title(value, show_title="", season=0, episode=0):
    text = str(value or "").strip()
    if not text:
        return ""

    text = re.sub(r"\.(mkv|mp4|avi|mov|m4v|ts)$", "", text, flags=re.IGNORECASE).strip()

    if show_title:
        escaped = re.escape(str(show_title).strip())
        text = re.sub(
            rf"^\s*{escaped}(?:\s*\([^)]*\))?\s*[-–—:]*\s*",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip()

    text = re.sub(r"\bS\d{1,2}E\d{1,3}\b", " ", text, flags=re.IGNORECASE)

    release_tokens = (
        r"WEB[- .]?DL|WEBRIP|BLURAY|BDRIP|BRRIP|HDTV|DVDRIP|"
        r"REMUX|2160P|1080P|720P|480P|HDR10\+?|HDR|DOLBY[ .]?VISION|"
        r"DV|HEVC|H\.?265|X265|H\.?264|X264|AV1|AAC|AC3|EAC3|"
        r"TRUEHD|ATMOS|DTS(?:-HD)?|DDP?\d(?:\.\d)?"
    )
    text = re.sub(
        rf"(?:\s*[-–—._ ]+\s*)?(?:{release_tokens})(?:\b.*)?$",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(r"[._]+", " ", text)
    text = re.sub(r"\s{2,}", " ", text)
    text = text.strip(" -–—:._")

    if show_title and text.casefold() == str(show_title).strip().casefold():
        return ""
    return text


def best_episode_title(episode, canonical, season, number):
    show_title = canonical.get("show_title") or episode.get("SeriesName") or ""

    # Apollo discovery metadata is the presentation authority when available.
    title = clean_episode_title(
        canonical.get("title") or "",
        show_title,
        season,
        number or 0,
    )
    if title:
        return title

    # Jellyfin remains the fallback for display metadata and the authority for
    # local availability, playback and resume state.
    title = clean_episode_title(
        episode.get("Name") or "",
        show_title,
        season,
        number or 0,
    )
    if title:
        return title

    return f"Episode {number}" if number is not None else "Episode"


def series_imdb_for_episode(jf, video, by_id, by_name):
    """Resolve an episode to its parent series IMDb id, never its episode id."""
    series_id = str(video.get("SeriesId") or "")
    if series_id and series_id not in by_id:
        try:
            series = jf.item(series_id)
            ids = series.get("ProviderIds") or {}
            by_id[series_id] = ids.get("Imdb") or ids.get("IMDb") or ""
        except Exception:
            by_id[series_id] = ""
    return (
        by_id.get(series_id, "")
        or by_name.get(str(video.get("SeriesName") or "").strip().lower(), "")
    )


def local_item_for_identity(jf, imdb_id, media_type="movie", season=0, episode=0):
    """Resolve a canonical IMDb(+S/E) identity back to its Jellyfin item.

    This is used when Apollo progress is newer than Jellyfin's resume list, so
    Continue Watching can still retain local-library capabilities.
    """
    if not jf or not imdb_id:
        return None
    key = str(imdb_id or "").strip().lower()
    try:
        if str(media_type or "movie") == "series" or int(episode or 0) > 0:
            series = (jf.series_index() or {}).get(key) or {}
            series_id = str(series.get("Id") or "")
            if not series_id:
                return None
            for item in jf.episodes(series_id):
                if (
                    int(item.get("ParentIndexNumber") or 0) == int(season or 0)
                    and int(item.get("IndexNumber") or 0) == int(episode or 0)
                ):
                    item["_ApolloSeriesImdb"] = imdb_id
                    item["_ApolloSeriesId"] = series_id
                    return item
            return None

        movie = (jf.library_index("movie") or {}).get(key) or {}
        item_id = str(movie.get("Id") or "")
        return jf.item(item_id) if item_id else None
    except Exception as exc:
        xbmc.log(f"[Apollo Media] Local identity lookup failed: {exc}", xbmc.LOGWARNING)
        return None


def continue_key(imdb_id="", season=0, episode=0, fallback_id=""):
    identity = str(imdb_id or fallback_id or "").strip().lower()
    if not identity:
        return ""
    return f"{identity}:{int(season or 0)}:{int(episode or 0)}"


def _cw_debug(context, event, **fields):
    try:
        payload = json.dumps(fields, sort_keys=True, separators=(",", ":"), default=str)
        xbmc.log(f"APOLLO_CW_DEBUG {context} {event} {payload}", xbmc.LOGINFO)
    except Exception:
        pass


def _cw_entry_title(entry):
    if entry.get("source") == "jellyfin":
        return str((entry.get("video") or {}).get("Name") or "Unknown")
    return str((entry.get("progress") or {}).get("title") or "Unknown")


def _cw_entry_debug_fields(entry, apollo_entry=None):
    source = entry.get("source") or ""
    video = entry.get("video") or {}
    progress_entry = apollo_entry or entry.get("progress") or {}
    user_data = video.get("UserData") or {}
    is_jellyfin = source == "jellyfin"
    item_type = str(video.get("Type") or "") if is_jellyfin else ""
    season = int(
        (video.get("ParentIndexNumber") if is_jellyfin else progress_entry.get("season"))
        or 0
    )
    episode = int(
        (video.get("IndexNumber") if is_jellyfin else progress_entry.get("episode"))
        or 0
    )
    media_type = (
        "series" if item_type == "Episode"
        else "movie" if is_jellyfin
        else str(progress_entry.get("media_type") or "movie")
    )
    jellyfin_raw = user_data.get("LastPlayedDate") if is_jellyfin else None
    return {
        "identity": entry.get("identity") or "",
        "title": _cw_entry_title(entry),
        "media_type": media_type,
        "season": season,
        "episode": episode,
        "jellyfin_item_id": str(video.get("Id") or "") if is_jellyfin else "",
        "jellyfin_lastplayed_raw": jellyfin_raw,
        "jellyfin_timestamp": _jellyfin_updated_epoch(user_data) if is_jellyfin else 0.0,
        "apollo_updated_raw": progress_entry.get("updated"),
        "apollo_position": progress_entry.get("position"),
        "apollo_duration": progress_entry.get("duration"),
        "activity_timestamp": float(entry.get("activity") or 0),
        "source": source,
        "jellyfin_backed": is_jellyfin,
    }


def ams_continue_watching_rows(sync_jellyfin=True):
    """Return AMS-owned profile Continue Watching, or None for legacy fallback."""
    try:
        rows = ams.continue_watching(
            ADDON,
            local_progress=progress.recent(),
            sync_jellyfin=sync_jellyfin,
        )
        if rows is not None:
            _cw_debug("AMS", "FETCH", count=len(rows))
        return rows
    except Exception as exc:
        xbmc.log(f"[Apollo Media] AMS Continue Watching unavailable: {exc}", xbmc.LOGWARNING)
        return None


def add_ams_continue_item(row, card_playback=False):
    jf = jellyfin()
    media_type = str(row.get("media_type") or "movie").lower()
    is_episode = media_type == "episode"
    imdb_id = str(row.get("imdb_id") or row.get("canonical_id") or "")
    jellyfin_item_id = str(row.get("jellyfin_item_id") or "")
    artwork_id = str(row.get("artwork_jellyfin_item_id") or jellyfin_item_id or "")
    title = str(row.get("title") or "Unknown")
    show_title = str(row.get("series_title") or "")
    season = int(row.get("season") or 0)
    episode = int(row.get("episode") or 0)
    position = max(0.0, float(row.get("position_seconds") or 0))
    duration = max(0.0, float(row.get("duration_seconds") or 0))
    label = title
    if is_episode:
        code = f"S{season:02d}E{episode:02d}"
        label = f"{show_title} • {code} • {title}" if show_title else f"{code} • {title}"

    item = xbmcgui.ListItem(label=literal_label(label))
    poster = jf.image_url(artwork_id) if artwork_id and jf.ready else public_art(imdb_id)
    set_metadata(item, title, imdb_id=imdb_id, poster=poster)
    tag = item.getVideoInfoTag()
    if is_episode:
        tag.setSeason(season)
        tag.setEpisode(episode)
        if show_title:
            tag.setTvShowTitle(show_title)
    if position > 0 and duration > 0:
        tag.setResumePoint(position, duration)
    item.setProperty("IsPlayable", "true")

    remote_type = "series" if is_episode else "movie"
    remote_auto = plugin_url(
        action="play_external", imdb=imdb_id, media_type=remote_type, season=season, episode=episode,
        title=title, resume_item_id=jellyfin_item_id, start_position=position, start_duration=duration,
        resume_mode="native",
    ) if imdb_id else ""
    remote_choose = plugin_url(
        action="remote_stream_list", imdb=imdb_id, media_type=remote_type, season=season, episode=episode,
        title=title, resume_item_id=jellyfin_item_id,
    ) if imdb_id else ""
    show_target = plugin_url(action="discovery_seasons", imdb=imdb_id, title=show_title or title, native_local="1") if is_episode and imdb_id else ""
    season_target = plugin_url(
        action="discovery_episodes", imdb=imdb_id, season=season, title=show_title or title, native_local="1",
        apollo_media_type="season", presentation_context="browse", in_library="1", show_title=show_title or title,
        show_target=show_target,
    ) if is_episode and imdb_id else ""

    if jellyfin_item_id:
        play_path = plugin_url(
            action="play_resolved" if card_playback else "play_jellyfin",
            source="jellyfin", item_id=jellyfin_item_id, title=title,
            apollo_media_type="episode" if is_episode else "movie", presentation_context="continue",
            imdb=imdb_id, jellyfin_item_id=jellyfin_item_id, show_title=show_title, season=season, episode=episode,
            in_library="1", show_target=show_target, season_target=season_target,
            remote_auto_target=remote_auto, remote_choose_target=remote_choose,
            remove_target=plugin_url(action="remove_continue", source="jellyfin", item_id=jellyfin_item_id, imdb=imdb_id, season=season, episode=episode),
        )
    else:
        play_path = remote_auto

    if imdb_id:
        item.addContextMenuItems([
            ("Play from Stream", f"RunPlugin({remote_auto})"),
            ("Choose Remote Stream", f"RunPlugin({remote_choose})"),
        ])
    xbmcplugin.addDirectoryItem(HANDLE, play_path, item, False)


def continue_watching_entries(jf, context="UNKNOWN"):
    """Build one deduplicated, newest-first timeline across both progress stores."""
    entries = []
    diagnostic_progress = {}
    seen = set()
    progress_entries = progress.recent()
    progress_by_identity = {}
    for entry in progress_entries:
        identity = continue_key(
            entry.get("imdb_id"), entry.get("season"), entry.get("episode")
        )
        if identity and _apollo_updated_epoch(entry) > _apollo_updated_epoch(
            progress_by_identity.get(identity)
        ):
            progress_by_identity[identity] = entry

    if jf:
        try:
            series_by_id = {}
            series_by_name = {
                str(value.get("Name") or "").strip().lower(): imdb
                for imdb, value in jf.series_index().items()
                if value.get("Name")
            }
            for video in jf.resume_items():
                provider_ids = video.get("ProviderIds") or {}
                imdb_id = provider_ids.get("Imdb") or provider_ids.get("IMDb") or ""
                season = int(video.get("ParentIndexNumber") or 0)
                episode = int(video.get("IndexNumber") or 0)
                if video.get("Type") == "Episode":
                    imdb_id = series_imdb_for_episode(
                        jf, video, series_by_id, series_by_name
                    )
                    video["_ApolloSeriesImdb"] = imdb_id

                fallback_id = (
                    video.get("SeriesId") if video.get("Type") == "Episode"
                    else video.get("Id")
                ) or video.get("Id") or ""
                identity = continue_key(imdb_id, season, episode, fallback_id)
                if identity and identity in seen:
                    continue
                if identity:
                    seen.add(identity)

                jellyfin_activity = _jellyfin_updated_epoch(
                    video.get("UserData") or {}
                )
                apollo_activity = _apollo_updated_epoch(
                    progress_by_identity.get(identity)
                )
                candidate = {
                    "identity": identity,
                    "source": "jellyfin",
                    "activity": max(jellyfin_activity, apollo_activity),
                    "imdb_id": imdb_id,
                    "video": video,
                }
                entries.append(candidate)
                diagnostic_progress[id(candidate)] = progress_by_identity.get(identity)
        except Exception as exc:
            notify(f"Could not load Continue Watching: {exc}", xbmcgui.NOTIFICATION_ERROR)

    for entry in progress_entries:
        identity = continue_key(
            entry.get("imdb_id"), entry.get("season"), entry.get("episode")
        )
        if identity and identity in seen:
            continue
        if identity:
            seen.add(identity)
        candidate = {
            "identity": identity,
            "source": "apollo",
            "activity": _apollo_updated_epoch(entry),
            "progress": entry,
        }
        entries.append(candidate)
        diagnostic_progress[id(candidate)] = entry

    for candidate_index, entry in enumerate(entries):
        _cw_debug(
            context,
            "BEFORE_SORT",
            candidate_index=candidate_index,
            **_cw_entry_debug_fields(entry, diagnostic_progress.get(id(entry))),
        )

    entries.sort(
        key=lambda entry: (
            1 if float(entry.get("activity") or 0) > 0 else 0,
            float(entry.get("activity") or 0),
        ),
        reverse=True,
    )
    _cw_debug(
        context,
        "AFTER_SORT_ORDER",
        titles=[_cw_entry_title(entry) for entry in entries],
    )
    for final_index, entry in enumerate(entries):
        _cw_debug(
            context,
            "FINAL_ENTRY",
            final_index=final_index,
            **_cw_entry_debug_fields(entry, diagnostic_progress.get(id(entry))),
        )
    return entries


def remote_card_targets(imdb_id, media_type, season=0, episode=0, title="", resume_item_id=""):
    """Return opaque Apollo plugin routes consumed by the card.

    The card never constructs provider URLs or knows provider details. It only
    receives addon-owned plugin routes for automatic remote playback and the
    headless stream picker.
    """
    imdb_id = str(imdb_id or "")
    if not imdb_id:
        return "", ""
    season = int(season or 0)
    episode = int(episode or 0)
    media_type = "series" if str(media_type or "").lower() in ("series", "episode", "show", "tv") else "movie"
    common = {
        "imdb": imdb_id,
        "media_type": media_type,
        "season": season,
        "episode": episode,
        "title": str(title or ""),
        "resume_item_id": str(resume_item_id or ""),
    }
    return (
        plugin_url(action="play_external", **common),
        plugin_url(action="remote_stream_list", **common),
    )


def add_remote_jellyfin_item(video, card_playback=False, episode_hint=None,
                             presentation_context="library", last_episode_added=""):
    item_id = video.get("Id") or ""
    item_type = video.get("Type") or "Movie"
    provider_ids = video.get("ProviderIds") or {}
    if item_type == "Episode":
        imdb_id = (video.get("_ApolloSeriesImdb")
                   or provider_ids.get("Imdb") or provider_ids.get("IMDb") or "")
        tmdb_id = video.get("_ApolloSeriesTmdb") or ""
    else:
        imdb_id = provider_ids.get("Imdb") or provider_ids.get("IMDb") or ""
        tmdb_id = provider_ids.get("Tmdb") or provider_ids.get("TMDb") or ""
    title = video.get("Name") or "Unknown"
    season = int(video.get("ParentIndexNumber") or 0)
    episode = int(video.get("IndexNumber") or 0)
    show_title = video.get("SeriesName") or ""
    card_media_type = _card_media_type(item_type, season, episode)
    if item_type == "Episode":
        label = f"{show_title} • S{season:02d}E{episode:02d} • {title}" if show_title else f"S{season:02d}E{episode:02d} • {title}"
    else:
        label = title
    item = xbmcgui.ListItem(label=label)
    set_metadata(
        item, title, video.get("Overview") or "", video.get("ProductionYear"),
        imdb_id, public_art(imdb_id), public_art(imdb_id, "background"),
    )
    tag = item.getVideoInfoTag()
    if item_type == "Episode":
        tag.setSeason(season)
        tag.setEpisode(episode)
        if show_title:
            tag.setTvShowTitle(show_title)
    user_data = video.get("UserData") or {}
    position = int(user_data.get("PlaybackPositionTicks") or 0) / 10000000
    duration = int(video.get("RunTimeTicks") or 0) / 10000000
    if position > 0 and duration > 0:
        tag.setResumePoint(position, duration)

    is_series = item_type == "Series"
    item.setProperty("IsPlayable", "false" if is_series else "true")

    show_target = ""
    season_target = ""
    if item_type == "Series":
        show_target = plugin_url(action="seasons", series_id=item_id, title=title, imdb=imdb_id, native_local="1")
    elif item_type == "Episode":
        series_id = str(video.get("SeriesId") or video.get("_ApolloSeriesId") or "")
        season_id = str(video.get("SeasonId") or "")
        if series_id:
            show_target = plugin_url(
                action="seasons", series_id=series_id, title=show_title, imdb=imdb_id,
                native_local="1", apollo_media_type="show", presentation_context="browse",
                in_library="1", jellyfin_item_id=series_id,
            )
            if season_id:
                season_target = plugin_url(
                    action="episodes", series_id=series_id, season_id=season_id, imdb=imdb_id,
                    title=show_title, native_local="1", apollo_media_type="season",
                    presentation_context="browse", in_library="1", jellyfin_item_id=season_id,
                    season=season, show_title=show_title, show_target=show_target,
                )
            elif imdb_id:
                # A local episode without Jellyfin SeasonId must never open the
                # unfiltered local-series episode route. Discovery can still
                # provide an exact season list and overlay local episodes.
                season_target = plugin_url(
                    action="discovery_episodes", imdb=imdb_id, season=season, title=show_title,
                    native_local="1", apollo_media_type="season", presentation_context="browse",
                    in_library="1", show_title=show_title, show_target=show_target,
                )
        elif imdb_id:
            show_target = plugin_url(action="discovery_seasons", imdb=imdb_id, title=show_title, native_local="1")
            season_target = plugin_url(
                action="discovery_episodes", imdb=imdb_id, season=season, title=show_title,
                native_local="1", apollo_media_type="season", presentation_context="browse",
                show_title=show_title, show_target=show_target,
            )

    remove_target = ""
    if presentation_context == "continue":
        remove_target = plugin_url(
            action="remove_continue", source="jellyfin", item_id=item_id,
            imdb=imdb_id, season=season, episode=episode,
        )

    remote_auto_target = ""
    remote_choose_target = ""
    if not is_series:
        remote_auto_target, remote_choose_target = remote_card_targets(
            imdb_id,
            "series" if item_type == "Episode" else "movie",
            season,
            episode,
            title,
            item_id,
        )

    card_play_target = ""
    if not is_series:
        card_play_target = plugin_url(
            action="play_resolved",
            source="jellyfin",
            item_id=item_id,
            title=title,
        )

    route_fields = _card_route_fields(
        media_type=card_media_type,
        presentation_context=presentation_context,
        imdb_id=imdb_id,
        tmdb_id=tmdb_id,
        jellyfin_item_id=item_id,
        show_title=show_title,
        season=season,
        episode=episode,
        release_date=video.get("PremiereDate") or "",
        date_added=video.get("DateCreated") or "",
        last_episode_added=last_episode_added,
        in_library=True,
        watched=bool(user_data.get("Played")),
        show_target=show_target,
        season_target=season_target,
        remove_target=remove_target,
        remote_auto_target=remote_auto_target,
        remote_choose_target=remote_choose_target,
        card_play_target=card_play_target,
    )

    if is_series:
        target = plugin_url(
            action="seasons", series_id=item_id, title=title, native_local="1",
            **route_fields,
        )
    else:
        target = plugin_url(
            action="play_resolved" if card_playback else "play_jellyfin_native",
            source="jellyfin", item_id=item_id, title=title, **route_fields,
        )
    xbmcplugin.addDirectoryItem(HANDLE, target, item, is_series)


def remote_jellyfin_library(item_type, sort_by="SortName", sort_order="Ascending",
                             limit=60, presentation_context="library", start_index=0):
    jf = require_jellyfin()
    xbmcplugin.setContent(HANDLE, "tvshows" if item_type == "Series" else "movies")
    if jf:
        try:
            hints = jellyfin_episode_hints(jf) if item_type == "Series" else {}
            fields = "ProviderIds,Overview,RunTimeTicks,UserData,Path,ImageTags,DateCreated,PremiereDate,SeriesId,SeriesName,SeasonId,ParentIndexNumber,IndexNumber"
            for video in jf.items(
                item_type, limit=limit, fields=fields,
                sort_by=sort_by, sort_order=sort_order, start_index=start_index,
            ):
                hint = hints.get(str(video.get("Id") or "")) if item_type == "Series" else None
                add_remote_jellyfin_item(
                    video, card_playback=True,
                    presentation_context=presentation_context,
                    last_episode_added=str((hint or {}).get("date_added") or ""),
                )
        except Exception as exc:
            notify(f"Could not load Jellyfin: {exc}", xbmcgui.NOTIFICATION_ERROR)
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)


def remote_continue_watching():
    xbmcplugin.setContent(HANDLE, "movies")
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_UNSORTED)
    rows = ams_continue_watching_rows(sync_jellyfin=True)
    if rows is not None:
        for row in rows:
            add_ams_continue_item(row, card_playback=True)
        xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)
        return
    jf = require_jellyfin()
    _cw_debug("HEADLESS", "CONSUMER_BEGIN", route="remote_continue_watching")
    entries = continue_watching_entries(jf, "HEADLESS")
    _cw_debug(
        "HEADLESS",
        "CONSUMER_ENTRIES",
        route="remote_continue_watching",
        entries_call_count=1,
        count=len(entries),
    )
    for final_index, entry in enumerate(entries):
        _cw_debug(
            "HEADLESS",
            "ADD_DIRECTORY_ITEM",
            final_index=final_index,
            identity=entry.get("identity") or "",
            title=_cw_entry_title(entry),
            source=entry.get("source") or "",
        )
        if entry["source"] == "jellyfin":
            add_remote_jellyfin_item(entry["video"], card_playback=True, presentation_context="continue")
        else:
            add_external_progress(entry["progress"], card_playback=True)
    _cw_debug(
        "HEADLESS",
        "CONSUMER_END",
        route="remote_continue_watching",
        dispatched_titles=[_cw_entry_title(entry) for entry in entries],
    )
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)


def popular_tv():
    jf = require_jellyfin()
    xbmcplugin.setContent(HANDLE, "tvshows")
    if jf:
        try:
            for media in media_service().popular_shows():
                render_show_media(media)
        except Exception as exc:
            notify(f"Could not load TV: {exc}", xbmcgui.NOTIFICATION_ERROR)
    xbmcplugin.endOfDirectory(HANDLE)

def search_tv():
    query = xbmcgui.Dialog().input("Search TV")
    xbmcplugin.setContent(HANDLE, "tvshows")
    if query:
        try:
            for series in search_series(query):
                add_discovery_series(
                    series,
                    local=None,
                    native_local=False,
                    presentation_context="search",
                )
        except Exception as exc:
            notify(f"TV search failed: {exc}", xbmcgui.NOTIFICATION_ERROR)
    xbmcplugin.endOfDirectory(HANDLE)

def library():
    jf = require_jellyfin()
    xbmcplugin.setContent(HANDLE, "movies")
    if jf:
        try:
            for media in media_service().library_movies():
                render_movie_media(media)
        except Exception as exc:
            notify(f"Could not load Jellyfin: {exc}", xbmcgui.NOTIFICATION_ERROR)
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)

def series_library():
    jf = require_jellyfin()
    xbmcplugin.setContent(HANDLE, "tvshows")
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
    if jf:
        try:
            for media in media_service().library_shows():
                render_show_media(media)
        except Exception as exc:
            notify(f"Could not load Jellyfin shows: {exc}", xbmcgui.NOTIFICATION_ERROR)
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)

def discovery_seasons(imdb_id, title, native_local=False):
    jf = jellyfin()
    xbmcplugin.setContent(HANDLE, "seasons")
    try:
        details = series_details(imdb_id)
        seasons = sorted({
            int(video.get("season") or 0)
            for video in details.get("videos", [])
        })

        local_season_numbers = set()
        if jf.ready:
            try:
                local_series = jf.find_series(imdb_id)
                if local_series:
                    for local_season in jf.seasons(local_series.get("Id") or ""):
                        local_season_numbers.add(
                            int(local_season.get("IndexNumber") or 0)
                        )
            except Exception as exc:
                xbmc.log(
                    f"[Apollo Media] Optional Jellyfin season enrichment failed: {exc}",
                    xbmc.LOGWARNING,
                )

        for season_number in seasons:
            add_discovery_season(
                imdb_id,
                season_number,
                title,
                season_number in local_season_numbers,
                native_local and jf.ready,
            )
    except Exception as exc:
        notify(f"Could not load seasons: {exc}", xbmcgui.NOTIFICATION_ERROR)
    xbmcplugin.endOfDirectory(HANDLE)

def discovery_episodes(imdb_id, season_number, native_local=False):
    jf = jellyfin()
    xbmcplugin.setContent(HANDLE, "episodes")
    try:
        details = series_details(imdb_id)
        discovered = [
            video for video in details.get("videos", [])
            if int(video.get("season") or 0) == int(season_number)
        ]
        discovered.sort(key=lambda video: int(video.get("episode") or 0))

        local_by_number = {}
        if jf.ready:
            try:
                local_series = jf.find_series(imdb_id)
                if local_series:
                    for episode in jf.episodes(local_series.get("Id")):
                        key = (
                            int(episode.get("ParentIndexNumber") or 0),
                            int(episode.get("IndexNumber") or 0),
                        )
                        local_by_number[key] = episode
            except Exception as exc:
                xbmc.log(
                    f"[Apollo Media] Optional Jellyfin episode enrichment failed: {exc}",
                    xbmc.LOGWARNING,
                )

        for episode in discovered:
            key = (
                int(episode.get("season") or 0),
                int(episode.get("episode") or 0),
            )
            add_discovery_episode(
                episode,
                imdb_id,
                local_by_number.get(key),
                native_local and jf.ready,
            )
    except Exception as exc:
        notify(f"Could not load episodes: {exc}", xbmcgui.NOTIFICATION_ERROR)
    xbmcplugin.endOfDirectory(HANDLE)

def show_seasons(series_id, imdb_id="", title="", native_local=False):
    jf = require_jellyfin()
    xbmcplugin.setContent(HANDLE, "seasons")
    if jf:
        try:
            for media in media_service().local_seasons(series_id, imdb_id, title):
                show_target = plugin_url(
                    action="seasons", series_id=series_id, title=title, imdb=imdb_id,
                    native_local="1" if native_local else "",
                    apollo_media_type="show", presentation_context="browse", in_library="1",
                    jellyfin_item_id=series_id,
                )
                target = plugin_url(
                    action="episodes",
                    series_id=series_id,
                    season_id=media.playback.get("season_id") or media.ids.jellyfin,
                    imdb=imdb_id,
                    title=media.show_title or title,
                    native_local="1" if native_local else "",
                    apollo_media_type="season", presentation_context="browse", in_library="1",
                    jellyfin_item_id=media.ids.jellyfin, season=media.season or 0,
                    show_title=media.show_title or title, show_target=show_target,
                )
                render_media_item(HANDLE, target, media, True)
        except Exception as exc:
            notify(f"Could not load seasons: {exc}", xbmcgui.NOTIFICATION_ERROR)
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)


def show_episodes(series_id, season_id, imdb_id="", title="", native_local=False):
    jf = require_jellyfin()
    xbmcplugin.setContent(HANDLE, "episodes")
    if jf:
        try:
            if not imdb_id and series_id:
                series_details = jf.item(series_id) or {}
                series_ids = series_details.get("ProviderIds") or {}
                imdb_id = series_ids.get("Imdb") or series_ids.get("IMDb") or ""
            for media in media_service().local_episodes(
                series_id,
                season_id,
                imdb_id,
                title,
            ):
                if imdb_id and media.ids.jellyfin:
                    media.playback["remote_auto_url"] = plugin_url(
                        action="play_external_prompt",
                        imdb=imdb_id,
                        media_type="series",
                        season=media.season or 0,
                        episode=media.episode or 0,
                        title=media.title,
                        resume_item_id=media.ids.jellyfin,
                    )
                    media.playback["remote_choose_url"] = plugin_url(
                        action="choose_external",
                        imdb=imdb_id,
                        media_type="series",
                        season=media.season or 0,
                        episode=media.episode or 0,
                        title=media.title,
                        resume_item_id=media.ids.jellyfin,
                    )
                show_target = plugin_url(
                    action="seasons", series_id=series_id, title=media.show_title or title, imdb=imdb_id,
                    native_local="1" if native_local else "",
                    apollo_media_type="show", presentation_context="browse", in_library="1",
                    jellyfin_item_id=series_id,
                )
                season_target = plugin_url(
                    action="episodes", series_id=series_id, season_id=season_id, imdb=imdb_id,
                    title=media.show_title or title, native_local="1" if native_local else "",
                    apollo_media_type="season", presentation_context="browse", in_library="1",
                    season=media.season or 0, show_title=media.show_title or title, show_target=show_target,
                )
                remote_auto_target, remote_choose_target = remote_card_targets(
                    imdb_id,
                    "series",
                    media.season or 0,
                    media.episode or 0,
                    media.title,
                    media.ids.jellyfin,
                )
                card_play_target = plugin_url(
                    action="play_resolved",
                    source="jellyfin",
                    item_id=media.ids.jellyfin,
                    title=media.title,
                )
                target = plugin_url(
                    action="play_jellyfin_native" if native_local else "play_jellyfin",
                    item_id=media.ids.jellyfin,
                    title=media.title,
                    apollo_media_type="episode", presentation_context="browse", in_library="1",
                    imdb=imdb_id, jellyfin_item_id=media.ids.jellyfin,
                    show_title=media.show_title or title, season=media.season or 0, episode=media.episode or 0,
                    show_target=show_target, season_target=season_target,
                    remote_auto_target=remote_auto_target,
                    remote_choose_target=remote_choose_target,
                    card_play_target=card_play_target,
                )
                render_media_item(HANDLE, target, media, False)
        except Exception as exc:
            notify(f"Could not load episodes: {exc}", xbmcgui.NOTIFICATION_ERROR)
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)


def continue_watching():
    xbmcplugin.setContent(HANDLE, "movies")
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_UNSORTED)
    rows = ams_continue_watching_rows(sync_jellyfin=True)
    if rows is not None:
        for row in rows:
            add_ams_continue_item(row, card_playback=False)
        xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)
        return
    jf = require_jellyfin()
    _cw_debug("GUI", "CONSUMER_BEGIN", route="continue_watching")
    entries = continue_watching_entries(jf, "GUI")
    _cw_debug(
        "GUI",
        "CONSUMER_ENTRIES",
        route="continue_watching",
        entries_call_count=1,
        count=len(entries),
    )
    for final_index, entry in enumerate(entries):
        _cw_debug(
            "GUI",
            "ADD_DIRECTORY_ITEM",
            final_index=final_index,
            identity=entry.get("identity") or "",
            title=_cw_entry_title(entry),
            source=entry.get("source") or "",
        )
        if entry["source"] == "apollo":
            add_external_progress(entry["progress"])
            continue

        video = entry["video"]
        if video.get("Type") == "Movie":
            add_jellyfin_movie(video, continue_item=True)
        elif video.get("Type") == "Episode":
            add_episode(
                video,
                entry.get("imdb_id") or "",
                force_series_art=True,
                continue_label=True,
            )
    _cw_debug(
        "GUI",
        "CONSUMER_END",
        route="continue_watching",
        dispatched_titles=[_cw_entry_title(entry) for entry in entries],
    )
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)


def add_external_progress(entry, card_playback=False):
    season = int(entry.get("season") or 0)
    episode = int(entry.get("episode") or 0)
    imdb_id = entry.get("imdb_id") or ""
    media_type = entry.get("media_type") or ("series" if episode else "movie")
    local_video = local_item_for_identity(
        require_jellyfin(), imdb_id, media_type, season, episode
    )
    local_item_id = str((local_video or {}).get("Id") or "")
    metadata = {}
    try:
        metadata = progress_metadata(
            imdb_id,
            entry.get("media_type") or "movie",
            season,
            episode,
        )
    except Exception as exc:
        xbmc.log(f"[Apollo Media] Progress metadata failed: {exc}", xbmc.LOGWARNING)
    title = metadata.get("title") or entry.get("title") or "Unknown"
    show_title = metadata.get("show_title") or ""

    if episode:
        code = f"S{season:02d}E{episode:02d}"
        label = f"{show_title} • {code} • {title}" if show_title else f"{code} • {title}"
    else:
        label = title

    item = xbmcgui.ListItem(label=label)
    set_metadata(
        item,
        title,
        metadata.get("plot") or "",
        metadata.get("year"),
        imdb_id,
        metadata.get("poster") or "",
        metadata.get("fanart") or "",
    )
    tag = item.getVideoInfoTag()
    if episode:
        tag.setSeason(season)
        tag.setEpisode(episode)
        if show_title:
            tag.setTvShowTitle(show_title)
    position = float(entry.get("position") or 0)
    duration = float(entry.get("duration") or 0)
    if position > 0 and duration > 0:
        tag.setResumePoint(position, duration)
    item.setProperty("IsPlayable", "true")
    item.addContextMenuItems([
        (
            "Choose Remote Stream",
            f"RunPlugin({plugin_url(action='choose_external', imdb=imdb_id, media_type=entry.get('media_type') or 'movie', season=season, episode=episode, title=title)})",
        ),
        (
            "Remove from Continue Watching",
            f"RunPlugin({plugin_url(action='remove_continue', source='apollo', imdb=imdb_id, season=season, episode=episode)})",
        ),
    ])

    show_target = ""
    season_target = ""
    if episode and imdb_id:
        show_target = plugin_url(action="discovery_seasons", imdb=imdb_id, title=show_title)
        season_target = plugin_url(
            action="discovery_episodes", imdb=imdb_id, season=season, title=show_title,
            show_title=show_title, show_target=show_target,
            apollo_media_type="season", presentation_context="browse",
        )
    remove_target = plugin_url(
        action="remove_continue", source="apollo", imdb=imdb_id,
        season=season, episode=episode,
    )
    remote_auto_target, remote_choose_target = remote_card_targets(
        imdb_id, media_type, season, episode, title, local_item_id
    )
    card_play_target = plugin_url(
        action="play_resolved",
        source="jellyfin",
        item_id=local_item_id,
        title=(local_video or {}).get("Name") or title,
    ) if local_item_id else ""

    route_fields = _card_route_fields(
        media_type="episode" if episode else "movie",
        presentation_context="continue",
        imdb_id=imdb_id,
        jellyfin_item_id=local_item_id,
        show_title=show_title,
        season=season,
        episode=episode,
        in_library=bool(local_item_id),
        show_target=show_target,
        season_target=season_target,
        remove_target=remove_target,
        remote_auto_target=remote_auto_target,
        remote_choose_target=remote_choose_target,
        card_play_target=card_play_target,
    )
    xbmcplugin.addDirectoryItem(
        HANDLE,
        plugin_url(
            action="play_resolved" if card_playback else "play_external_resolved_prompt",
            source="remote",
            media_type=media_type,
            resume_item_id=local_item_id,
            title=title,
            **route_fields,
        ),
        item,
        False,
    )


def play_discovery(imdb_id, title):
    play_resolved(
        "ams",
        imdb_id=imdb_id,
        media_type="movie",
        title=title,
    )

def _jellyfin_updated_epoch(user_data):
    value = str((user_data or {}).get("LastPlayedDate") or "").strip()
    if not value:
        return 0.0
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.timestamp()
    except Exception:
        return 0.0


def _apollo_updated_epoch(entry):
    try:
        activity = float((entry or {}).get("updated") or 0)
        return activity if activity > 0 and math.isfinite(activity) else 0.0
    except (TypeError, ValueError):
        return 0.0


def canonical_local_resume(imdb_id, media_type, season, episode, title, item_id):
    """
    One logical progress value per media identity.

    Apollo remembers the last Jellyfin position it synchronized. If Jellyfin
    later reports a materially different position, that is treated as an
    external Jellyfin-app change and imported into Apollo.
    """
    season = int(season or 0)
    episode = int(episode or 0)
    saved = progress.get(imdb_id, season, episode) if imdb_id else None

    if not item_id:
        if saved:
            return float(saved.get("position") or 0), float(saved.get("duration") or 0)
        return 0, 0

    try:
        details = jellyfin().item(item_id) or {}
    except Exception as exc:
        xbmc.log(f"[Apollo Media] Jellyfin progress read failed: {exc}", xbmc.LOGWARNING)
        if saved:
            return float(saved.get("position") or 0), float(saved.get("duration") or 0)
        return 0, 0

    user_data = details.get("UserData") or {}
    jf_position = int(user_data.get("PlaybackPositionTicks") or 0) / 10000000
    jf_duration = int(details.get("RunTimeTicks") or 0) / 10000000
    jellyfin_activity = _jellyfin_updated_epoch(user_data)
    saved_activity = _apollo_updated_epoch(saved)
    sync_activity = jellyfin_activity or saved_activity or 0.0

    if not imdb_id:
        return jf_position, jf_duration

    # No canonical row yet: import Jellyfin and establish the sync snapshot.
    if not saved:
        if jf_position > 0 and jf_duration > 0:
            progress.save(
                imdb_id, media_type, season, episode, title,
                jf_position, jf_duration,
                updated=sync_activity,
                jellyfin_synced_position=jf_position,
            )
        return jf_position, jf_duration

    snapshot = float(saved.get("jellyfin_synced_position", -1))
    apollo_position = float(saved.get("position") or 0)
    apollo_duration = float(saved.get("duration") or 0)

    # First run after upgrading: current Jellyfin wins once. This also removes
    # stale pre-unification remote-stream positions.
    if snapshot < 0:
        if jf_position > 0 and jf_duration > 0:
            progress.save(
                imdb_id, media_type, season, episode, title,
                jf_position, jf_duration,
                updated=sync_activity,
                jellyfin_synced_position=jf_position,
            )
        else:
            progress.remove(imdb_id, season, episode)
        return jf_position, jf_duration

    # Jellyfin moved since Apollo last synchronized it. That means playback
    # happened outside Apollo/Kodi, so import the Jellyfin position.
    if abs(jf_position - snapshot) > 3:
        if jf_position > 0 and jf_duration > 0:
            progress.save(
                imdb_id, media_type, season, episode, title,
                jf_position, jf_duration,
                updated=sync_activity,
                jellyfin_synced_position=jf_position,
            )
        else:
            progress.remove(imdb_id, season, episode)
        return jf_position, jf_duration

    # Jellyfin still matches our last sync snapshot. Apollo's identity ledger
    # is therefore the newest value.
    return apollo_position, apollo_duration




def jellyfin_resume(item_id, imdb_id="", media_type="movie", season=0, episode=0, title=""):
    return canonical_local_resume(
        imdb_id, media_type, int(season or 0), int(episode or 0), title, item_id
    )


def format_resume_time(seconds):
    total = max(0, int(float(seconds or 0)))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def choose_resume_start(imdb_id, media_type, season=0, episode=0, title="", resume_item_id=""):
    season = int(season or 0)
    episode = int(episode or 0)

    position, duration = jellyfin_resume(
        resume_item_id,
        imdb_id,
        media_type,
        season,
        episode,
        title,
    )

    chosen_position = float(position or 0)
    duration = float(duration or 0)

    if chosen_position > 0:
        choice = xbmcgui.Dialog().contextmenu([
            f"Resume from {format_resume_time(chosen_position)}",
            "Start from beginning",
        ])
        if choice < 0:
            return None

        if choice == 1:
            chosen_position = 0.0
            if imdb_id:
                progress.remove(imdb_id, season, episode)
                source_session.clear_resume(imdb_id, season, episode)

            if resume_item_id:
                try:
                    jellyfin().set_resume(resume_item_id, 0)
                except Exception as exc:
                    xbmc.log(
                        f"[Apollo Media] Could not reset Jellyfin resume: {exc}",
                        xbmc.LOGWARNING,
                    )

    return chosen_position, duration


def play_external_prompt(imdb_id, media_type, season=None, episode=None, title="", resume_item_id=""):
    season = int(season or 0)
    episode = int(episode or 0)

    chosen = choose_resume_start(
        imdb_id, media_type, season, episode, title, resume_item_id
    )
    if chosen is None:
        return

    chosen_position, duration = chosen
    target = plugin_url(
        action="play_external",
        imdb=imdb_id,
        media_type=media_type,
        season=season,
        episode=episode,
        title=title,
        resume_item_id=resume_item_id,
        start_position=chosen_position,
        start_duration=duration,
    )
    xbmc.executebuiltin(f"PlayMedia({target})")


def play_external_resolved_prompt(imdb_id, media_type, season=None, episode=None, title="", resume_item_id=""):
    """Resolve remote playback after Kodi has handled its native resume choice.

    Items opened from Kodi already carry a resume point, so Kodi owns the one
    Resume / Start from beginning dialog. Apollo must not ask the same question
    a second time inside the resolver.
    """
    play_external(
        imdb_id,
        media_type,
        int(season or 0),
        int(episode or 0),
        title,
        resume_item_id,
        None,
        None,
        "native",
    )


def play_external(imdb_id, media_type, season=None, episode=None, title="", resume_item_id="", start_position=None, start_duration=None, resume_mode=""):
    token = ADDON.getSettingString("torbox_token")
    if not token:
        notify("Link TorBox before playing remote sources", xbmcgui.NOTIFICATION_WARNING)
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return
    try:
        streams = external_streams(token, imdb_id, media_type, season, episode)
    except Exception as exc:
        notify(f"Source search failed: {exc}", xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return
    if not streams:
        notify("No cached TorBox source was found", xbmcgui.NOTIFICATION_WARNING)
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return
    resume_position, resume_duration, session_resume_mode = resolve_remote_position(
        resume_mode,
        start_position,
        start_duration,
        lambda: jellyfin_resume(
            resume_item_id, imdb_id, media_type, season, episode, title
        ),
    )

    source_session.save(
        streams, imdb_id, media_type, season, episode, title,
        resume_position, resume_duration, resume_item_id,
        session_resume_mode,
    )
    playback_session.save(
        "remote", imdb_id, media_type, season, episode, title,
        jellyfin_item_id=resume_item_id,
        requested_start_position=resume_position,
        requested_duration=resume_duration,
        resume_mode=session_resume_mode,
    )
    selected = source_session.current()
    if not selected:
        notify("No unflagged stream is available", xbmcgui.NOTIFICATION_WARNING)
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return
    item = external_item(
        selected.get("url") or "", title, imdb_id, media_type, season, episode,
        resume_position, resume_duration,
    )
    xbmcplugin.setResolvedUrl(HANDLE, True, item)


def external_item(url, title, imdb_id, media_type, season=None, episode=None,
                  position=None, duration=None):
    item = xbmcgui.ListItem(label=title, path=url)
    tag = item.getVideoInfoTag()
    tag.setTitle(literal_label(title))
    tag.setUniqueID(imdb_id, "imdb")
    if media_type == "series":
        tag.setSeason(int(season or 0))
        tag.setEpisode(int(episode or 0))
    saved = progress.get(imdb_id, season or 0, episode or 0)
    if position is None and saved:
        position, duration = saved.get("position"), saved.get("duration")

    # PlaybackSession is the authority that decides the canonical absolute
    # position. Kodi's native player adapter applies that position during
    # initial Player.Open by consuming this resume point. PlaybackMonitor does
    # not re-apply initial Resume/Start Over after AVStart.
    if position and duration:
        tag.setResumePoint(float(position), float(duration))

    item.setProperty("IsPlayable", "true")
    return item


def current_stream_info():
    session = source_session.load() or {}
    streams = session.get("streams") or []

    if not streams:
        notify("No active Apollo stream session", xbmcgui.NOTIFICATION_WARNING)
        return

    try:
        index = int(session.get("index") or 0)
    except Exception:
        index = 0

    if index < 0 or index >= len(streams):
        notify("No active Apollo stream session", xbmcgui.NOTIFICATION_WARNING)
        return

    stream = streams[index]
    provider = str(stream.get("provider") or "Unknown provider")
    title = str(
        stream.get("title")
        or stream.get("description")
        or stream.get("url")
        or "Unknown stream"
    )

    flag = source_session.flag_for_url(stream.get("url") or "")
    if flag:
        reason = str(flag.get("reason") or "flagged").replace("_", " ").title()
        flagged_text = f"Yes - {reason}"
    else:
        flagged_text = "No"

    heading = f"Current Stream - {provider} - {index + 1}/{len(streams)}"
    xbmcgui.Dialog().ok(
        heading,
        f"Flagged: {flagged_text}\n\n{title}",
    )


def play_next_stream(show_notice=True):
    player = xbmc.Player()
    try:
        position = player.getTime() if player.isPlayingVideo() else 0
        duration = player.getTotalTime() if player.isPlayingVideo() else 0
    except Exception:
        position, duration = 0, 0

    session, stream = source_session.advance()
    if not session or not stream:
        notify("No more compatible streams are available", xbmcgui.NOTIFICATION_WARNING)
        return False

    source_session.update_resume(position, duration, "live")
    playback_session.request_start(position, duration, "live")

    item = external_item(
        stream.get("url") or "", session.get("title") or "",
        session.get("imdb_id") or "", session.get("media_type") or "movie",
        session.get("season"), session.get("episode"), position, duration,
    )
    player.play(stream.get("url") or "", item)

    if show_notice:
        notify("Trying the next stream")
    return True


def learn_from_flag(reason, stream):
    text = f"{stream.get('title', '')} {stream.get('description', '')}".lower()
    setting = ""
    if reason == "bad_colors":
        if any(marker in text for marker in ("dolby vision", "dovi", " dv ")):
            setting = "allow_dolby_vision"
        elif "hdr10+" in text or "hdr10plus" in text:
            setting = "allow_hdr10plus"
        elif "hdr" in text:
            setting = "allow_hdr10"
    elif reason == "no_audio":
        for candidate, markers in (
            ("allow_truehd", ("truehd", "atmos")),
            ("allow_dtshd", ("dts-hd", "dtshd", "dts:x", "dtsx")),
            ("allow_eac3", ("eac3", "e-ac-3", "dd+")),
            ("allow_ac3", ("ac3", "ac-3")),
            ("allow_dts", (" dts ",)),
        ):
            if any(marker in f" {text} " for marker in markers):
                setting = candidate
                break
    elif reason == "unsupported_codec":
        for candidate, markers in (
            ("allow_av1", ("av1", "av01")),
            ("allow_hevc", ("hevc", "h265", "h.265", "x265")),
            ("allow_h264", ("h264", "h.264", "x264", "avc")),
        ):
            if any(marker in text for marker in markers):
                setting = candidate
                break
    if setting:
        ADDON.setSettingBool(setting, False)
        notify("Device profile updated; trying the next stream")


def flag_current(reason=""):
    stream = source_session.current()
    if not stream:
        notify("There is no active Apollo stream to flag", xbmcgui.NOTIFICATION_WARNING)
        return
    reasons = [
        ("bad_colors", "Bad colors / HDR"),
        ("no_audio", "No audio"),
        ("unsupported_codec", "Unsupported codec"),
        ("buffering", "Buffering"),
        ("wrong_content", "Wrong content"),
        ("wrong_language", "Wrong language"),
    ]
    if not reason:
        choice = xbmcgui.Dialog().select("What is wrong with this stream?", [label for _, label in reasons])
        if choice < 0:
            return
        reason = reasons[choice][0]
    source_session.flag(reason)
    learn_from_flag(reason, stream)
    play_next_stream(show_notice=False)


def enabled_source_providers():
    providers = []
    if ADDON.getSettingBool("provider_comet"):
        providers.append("comet")
    if ADDON.getSettingBool("provider_torrentio"):
        providers.append("torrentio")
    if ADDON.getSettingBool("provider_debridio"):
        providers.append("debridio")
    return providers


def external_streams(token, imdb_id, media_type, season=None, episode=None):
    providers = enabled_source_providers()
    if not providers:
        notify(
            "Enable at least one source provider in Apollo Media settings",
            xbmcgui.NOTIFICATION_WARNING,
        )
        return []

    return find_streams(
        token,
        providers,
        imdb_id,
        media_type,
        int(season) if season is not None else None,
        int(episode) if episode is not None else None,
        compatibility_profile(ADDON),
        ADDON.getSettingString("debridio_url"),
    )


def remote_stream_list(imdb_id, media_type, season=None, episode=None, title="", resume_item_id=""):
    """Headless ranked stream list for Home Assistant/card clients."""
    token = ADDON.getSettingString("torbox_token")
    xbmcplugin.setContent(HANDLE, "files")
    if not token or not imdb_id:
        xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)
        return

    season = int(season or 0)
    episode = int(episode or 0)
    session = source_session.load() or {}
    same_identity = bool(
        session
        and str(session.get("imdb_id") or "").strip().lower() == str(imdb_id or "").strip().lower()
        and int(session.get("season") or 0) == season
        and int(session.get("episode") or 0) == episode
    )

    if not same_identity:
        try:
            streams = external_streams(token, imdb_id, media_type, season, episode)
        except Exception as exc:
            xbmc.log(f"[Apollo Media] Headless stream search failed: {exc}", xbmc.LOGERROR)
            xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)
            return
        if not streams:
            xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)
            return
        resume_position, resume_duration = jellyfin_resume(
            resume_item_id, imdb_id, media_type, season, episode, title
        )
        session = source_session.save(
            streams, imdb_id, media_type, season, episode, title,
            resume_position, resume_duration, resume_item_id,
        )

    flags_by_url = {
        str(entry.get("url") or ""): entry
        for entry in (session.get("flags") or [])
    }
    current_index = -1
    try:
        player = xbmc.Player()
        selected = source_session.current() or {}
        if (
            player.isPlayingVideo()
            and selected
            and player.getPlayingFile() == str(selected.get("url") or "")
        ):
            current_index = int(session.get("index") or 0)
    except Exception:
        current_index = -1

    rows = []
    for index, stream in enumerate(session.get("streams") or []):
        flagged = str(stream.get("url") or "") in flags_by_url
        rows.append((flagged, index, stream))

    # Match Kodi chooser behavior: clean sources first, stable original ranking.
    rows.sort(key=lambda row: (1 if row[0] else 0, row[1]))

    for flagged, index, stream in rows:
        provider = str(stream.get("provider") or "Unknown")
        title_text = str(stream.get("title") or stream.get("description") or f"Stream {index + 1}")
        item = xbmcgui.ListItem(label=title_text)
        tag = item.getVideoInfoTag()
        tag.setTitle(title_text)
        if stream.get("description"):
            tag.setPlot(str(stream.get("description") or ""))
        item.setProperty("IsPlayable", "true")
        target = plugin_url(
            action="play_session_stream",
            index=index,
            apollo_stream_index=index,
            apollo_stream_count=len(session.get("streams") or []),
            apollo_provider=provider,
            apollo_flagged="1" if flagged else "0",
            apollo_current="1" if index == current_index else "0",
            apollo_quality=str(stream.get("quality") or "Other"),
            apollo_video_info=str(stream.get("video") or ""),
            apollo_audio_info=str(stream.get("audio") or ""),
        )
        xbmcplugin.addDirectoryItem(HANDLE, target, item, False)

    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)


def manual_flag_stream(index):
    reasons = [
        ("bad_colors", "Bad colors / HDR"),
        ("no_audio", "No audio"),
        ("unsupported_codec", "Unsupported codec"),
        ("buffering", "Buffering"),
        ("wrong_content", "Wrong content"),
        ("wrong_language", "Wrong language"),
    ]
    choice = xbmcgui.Dialog().select(
        "Flag Stream",
        [label for _, label in reasons],
    )
    if choice < 0:
        return

    reason = reasons[choice][0]
    stream = source_session.flag_index(index, reason)
    if not stream:
        notify("That stream session has expired", xbmcgui.NOTIFICATION_WARNING)
        return

    learn_from_flag(reason, stream)
    notify("Stream flagged", xbmcgui.NOTIFICATION_INFO)


def manual_unflag_stream(index):
    if source_session.unflag_index(index):
        notify("Stream unflagged", xbmcgui.NOTIFICATION_INFO)
    else:
        notify("Stream was not flagged", xbmcgui.NOTIFICATION_INFO)


def choose_external(imdb_id, media_type, season=None, episode=None, title="", resume_item_id=""):
    token = ADDON.getSettingString("torbox_token")
    if not token:
        notify("Link TorBox before choosing remote sources", xbmcgui.NOTIFICATION_WARNING)
        return

    season = int(season or 0)
    episode = int(episode or 0)

    try:
        streams = external_streams(token, imdb_id, media_type, season, episode)
        if not streams:
            notify("No cached TorBox source was found", xbmcgui.NOTIFICATION_WARNING)
            return

        resume_position, resume_duration = jellyfin_resume(
            resume_item_id, imdb_id, media_type, season, episode, title
        )

        session = source_session.save(
            streams, imdb_id, media_type, season, episode, title,
            resume_position, resume_duration, resume_item_id,
        )

        while True:
            flags_by_url = {
                str(entry.get("url") or ""): entry
                for entry in (session.get("flags") or [])
            }

            rows = []
            for original_index, row in enumerate(session.get("streams") or []):
                rows.append({
                    "index": original_index,
                    "stream": row,
                    "flagged": str(row.get("url") or "") in flags_by_url,
                })

            rows.sort(key=lambda row: (1 if row["flagged"] else 0, row["index"]))

            dialog = StreamChooserDialog(
                "StreamChooser.xml",
                ADDON.getAddonInfo("path"),
                "Default",
                "1080i",
                streams=rows,
                flags=flags_by_url,
            )
            dialog.doModal()
            result = dialog.result
            del dialog

            if not result:
                return

            action, original_index = result

            if action == "flag":
                manual_flag_stream(original_index)
                session = source_session.load() or session
                continue

            if action == "unflag":
                manual_unflag_stream(original_index)
                session = source_session.load() or session
                continue

            if action == "play":
                target = plugin_url(
                    action="play_session_stream",
                    index=original_index,
                )
                xbmc.executebuiltin(f"PlayMedia({target})")
                return

    except Exception as exc:
        xbmc.log(f"[Apollo Media] Custom stream chooser failed: {exc}", xbmc.LOGERROR)
        notify(f"Source search failed: {exc}", xbmcgui.NOTIFICATION_ERROR)


def play_session_stream(index, start_position=None, start_duration=None, resume_mode=""):
    session, stream = source_session.select(index)
    if not session or not stream:
        notify("That stream session has expired", xbmcgui.NOTIFICATION_WARNING)
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return
    if start_position not in (None, ""):
        position = float(start_position or 0)
        duration = float(start_duration or 0)
        mode = str(resume_mode or "live")
        session = source_session.update_resume(position, duration, mode) or session
    else:
        position = float(session.get("resume_position") or 0)
        duration = float(session.get("resume_duration") or 0)
        mode = str(session.get("resume_mode") or "native")
    playback_session.save(
        "remote",
        session.get("imdb_id") or "",
        session.get("media_type") or "movie",
        session.get("season"),
        session.get("episode"),
        session.get("title") or "",
        jellyfin_item_id=session.get("jellyfin_item_id") or "",
        requested_start_position=position,
        requested_duration=duration,
        resume_mode=mode,
    )
    item = external_item(
        stream.get("url") or "", session.get("title") or "",
        session.get("imdb_id") or "", session.get("media_type") or "movie",
        session.get("season"), session.get("episode"), position, duration,
    )
    xbmcplugin.setResolvedUrl(HANDLE, True, item)


def show_on_tv(path):
    prefix = "plugin://plugin.video.apollomedia"
    if not path.startswith(prefix):
        notify("Apollo can only show its own pages", xbmcgui.NOTIFICATION_WARNING)
        return
    safe_path = path.replace('"', '%22')
    xbmc.executebuiltin("ActivateWindow(10025)")
    xbmc.sleep(250)
    xbmc.executebuiltin(f'Container.Update("{safe_path}",replace)')



def resolved_playback_item(source, item_id="", imdb_id="", media_type="movie",
                           season=0, episode=0, title="", resume_item_id="",
                           resume_mode=""):
    """Resolve Jellyfin or remote media into the same final Kodi ListItem."""
    season = int(season or 0); episode = int(episode or 0)

    if source == "ams":
        if not imdb_id:
            raise RuntimeError("Missing Apollo playback identity")
        if not ams.configured(ADDON):
            raise RuntimeError("AMS URL is not configured")
        if not ams.device_key(ADDON):
            raise RuntimeError("AMS device key is not configured")

        saved = progress.get(imdb_id, season, episode) or {}
        position = float(saved.get("position") or 0)
        duration = float(saved.get("duration") or 0)

        if resume_mode == "start_over":
            position = 0

        ams_decision = ams.resolve_playback_for_identity(
            ADDON, imdb_id, media_type, season, episode
        )

        # AMS may legitimately not contain a discovery-only title. That means
        # it is not locally available and the normal remote provider path wins.
        if not ams_decision:
            xbmc.log(
                f"[Apollo Media] AMS has no media row for {imdb_id} "
                f"S{season:02d}E{episode:02d}; using remote playback",
                xbmc.LOGINFO,
            )
            return resolved_playback_item(
                "remote", "", imdb_id, media_type, season, episode, title,
                "", resume_mode
            )

        mode = str(ams_decision.get("mode") or "")

        if mode == "remote":
            xbmc.log(
                f"[Apollo Media] AMS selected remote playback for {imdb_id} "
                f"S{season:02d}E{episode:02d}: "
                f"{ams_decision.get('reason') or 'fallback_required'}",
                xbmc.LOGINFO,
            )
            return resolved_playback_item(
                "remote", "", imdb_id, media_type, season, episode, title,
                "", resume_mode
            )

        playback_path = str(
            ams_decision.get("playback_path") or ""
        ).strip()

        if mode == "local" and playback_path:
            xbmc.log(
                f"[Apollo Media] AMS local playback via "
                f"{ams_decision.get('provider') or 'local'}: "
                f"{playback_path}",
                xbmc.LOGINFO,
            )

            item = external_item(
                playback_path,
                title,
                imdb_id,
                media_type,
                season,
                episode,
                position,
                duration,
            )

            if resume_mode == "start_over":
                item.setProperty("StartOffset", "0")

            media = ams_decision.get("media") or {}
            show_title = str(media.get("series_title") or "")
            if episode and show_title:
                item.getVideoInfoTag().setTvShowTitle(show_title)

            active_media.save({
                "source": "local",
                "transport": "ams",
                "provider": str(ams_decision.get("provider") or ""),
                "playback_path": playback_path,
                "jellyfin_item_id": "",
                "imdb_id": str(imdb_id),
                "media_type": media_type,
                "season": season,
                "episode": episode,
                "title": title,
                "show_title": show_title,
            })

            playback_session.save(
                "ams_local",
                imdb_id,
                media_type,
                season,
                episode,
                title,
                jellyfin_item_id="",
                requested_start_position=position,
                requested_duration=duration,
                resume_mode=resume_mode or "native",
            )
            return item

        raise RuntimeError(
            f"AMS returned an invalid playback decision for "
            f"{imdb_id}: {ams_decision}"
        )

    if source == "jellyfin":
        jf = require_jellyfin()
        if not jf or not item_id: raise RuntimeError("Missing Jellyfin playback identity")
        details = jf.item(item_id); item_type = details.get("Type") or "Movie"
        season = int(details.get("ParentIndexNumber") or season or 0)
        episode = int(details.get("IndexNumber") or episode or 0)
        media_type = "series" if item_type == "Episode" else "movie"
        ids = details.get("ProviderIds") or {}; imdb_id = ids.get("Imdb") or ids.get("IMDb") or imdb_id
        if item_type == "Episode" and details.get("SeriesId"):
            try:
                series = jf.item(details.get("SeriesId")) or {}; ids = series.get("ProviderIds") or {}
                imdb_id = ids.get("Imdb") or ids.get("IMDb") or imdb_id
            except Exception: pass
        title = title or details.get("Name") or ""
        position, duration = canonical_local_resume(imdb_id, media_type, season, episode, title, item_id)
        if resume_mode == "start_over": position = 0

        ams_decision = ams.resolve_playback_for_identity(
            ADDON, imdb_id, media_type, season, episode
        )
        if ams_decision:
            mode = str(ams_decision.get("mode") or "")
            if mode == "remote":
                xbmc.log(
                    f"[Apollo Media] AMS selected remote playback for {imdb_id} "
                    f"S{season:02d}E{episode:02d}: {ams_decision.get('reason') or 'fallback_required'}",
                    xbmc.LOGINFO,
                )
                return resolved_playback_item(
                    "remote", "", imdb_id, media_type, season, episode, title,
                    item_id, resume_mode
                )

            playback_path = str(ams_decision.get("playback_path") or "").strip()
            if mode == "local" and playback_path:
                xbmc.log(
                    f"[Apollo Media] AMS local playback via {ams_decision.get('provider') or 'local'}: "
                    f"{playback_path}",
                    xbmc.LOGINFO,
                )
                item = external_item(
                    playback_path, title, imdb_id, media_type, season, episode,
                    position, duration
                )
                if resume_mode == "start_over":
                    item.setProperty("StartOffset", "0")
                tag = item.getVideoInfoTag()
                tag.setUniqueID(item_id, "jellyfin")
                if item_type == "Episode" and details.get("SeriesName"):
                    tag.setTvShowTitle(details.get("SeriesName"))
                active_media.save({
                    "source": "local",
                    "transport": "ams",
                    "provider": str(ams_decision.get("provider") or ""),
                    "jellyfin_item_id": str(item_id),
                    "imdb_id": str(imdb_id),
                    "media_type": media_type,
                    "season": season,
                    "episode": episode,
                    "title": title,
                    "show_title": details.get("SeriesName") or "",
                })
                playback_session.save(
                    "ams_local", imdb_id, media_type, season, episode, title,
                    jellyfin_item_id=item_id,
                    requested_start_position=position,
                    requested_duration=duration,
                    resume_mode=resume_mode or "native",
                )
                return item

            raise RuntimeError(
                f"AMS returned an invalid playback decision for {imdb_id}: {ams_decision}"
            )

        item = external_item(jf.stream_url(item_id), title, imdb_id, media_type, season, episode, position, duration)
        if resume_mode == "start_over":
            item.setProperty("StartOffset", "0")
        tag=item.getVideoInfoTag(); tag.setUniqueID(item_id,"jellyfin")
        if item_type=="Episode" and details.get("SeriesName"): tag.setTvShowTitle(details.get("SeriesName"))
        active_media.save({"source":"local","jellyfin_item_id":str(item_id),"imdb_id":str(imdb_id),
                           "media_type":media_type,"season":season,"episode":episode,"title":title,
                           "show_title":details.get("SeriesName") or ""})
        playback_session.save(
            "jellyfin", imdb_id, media_type, season, episode, title,
            jellyfin_item_id=item_id,
            requested_start_position=position,
            requested_duration=duration,
            resume_mode=resume_mode or "native",
        )
        return item
    if source == "remote":
        token=ADDON.getSettingString("torbox_token")
        if not token: raise RuntimeError("Link TorBox before playing remote sources")
        streams=external_streams(token,imdb_id,media_type,season,episode)
        if not streams: raise RuntimeError("No cached TorBox source was found")
        position,duration,session_mode=resolve_remote_position(
            resume_mode,None,None,lambda: jellyfin_resume(resume_item_id,imdb_id,media_type,season,episode,title))
        source_session.save(streams,imdb_id,media_type,season,episode,title,position,duration,resume_item_id,session_mode)
        selected=source_session.current()
        if not selected: raise RuntimeError("No unflagged stream is available")
        playback_session.save(
            "remote", imdb_id, media_type, season, episode, title,
            jellyfin_item_id=resume_item_id,
            requested_start_position=position,
            requested_duration=duration,
            resume_mode=session_mode,
        )
        return external_item(selected.get("url") or "",title,imdb_id,media_type,season,episode,position,duration)
    raise RuntimeError(f"Unsupported Apollo playback source: {source}")

def play_resolved(source, item_id="", imdb_id="", media_type="movie", season=0,
                  episode=0, title="", resume_item_id="", resume_mode=""):
    """The single card playback entry point."""
    try:
        xbmcplugin.setResolvedUrl(HANDLE, True, resolved_playback_item(
            source,item_id,imdb_id,media_type,season,episode,title,resume_item_id,resume_mode))
    except Exception as exc:
        xbmc.log(f"[Apollo Media] Unified playback failed: {exc}", xbmc.LOGERROR)
        notify(f"Playback failed: {exc}", xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())


def play_jellyfin(item_id, title, start_over=False):
    """Resolve normal local clicks through Apollo's unified playback path."""
    play_resolved(
        "jellyfin",
        item_id=item_id,
        title=title,
        resume_mode="start_over" if start_over else "",
    )


def remote_play_jellyfin(item_id, title="", resume_mode="", start_position=None, start_duration=None):
    """Resolve Jellyfin to an HTTP URL for a headless Player.Open handoff.

    For live remote -> local switching, the current absolute position is
    carried as a ResumePoint and consumed by Kodi's initial Player.Open
    options.resume path. PlaybackMonitor must not re-seek after AVStart.
    """
    jf = require_jellyfin()
    if not jf or not item_id:
        xbmc.log("[Apollo Media] Headless local playback missing Jellyfin item", xbmc.LOGERROR)
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return
    try:
        details = jf.item(item_id)
        item_type = details.get("Type") or "Movie"
        season = int(details.get("ParentIndexNumber") or 0)
        episode = int(details.get("IndexNumber") or 0)
        media_type = "series" if item_type == "Episode" else "movie"

        ids = details.get("ProviderIds") or {}
        imdb_id = ids.get("Imdb") or ids.get("IMDb") or ""
        if item_type == "Episode" and details.get("SeriesId"):
            try:
                series = jf.item(details.get("SeriesId")) or {}
                sids = series.get("ProviderIds") or {}
                imdb_id = sids.get("Imdb") or sids.get("IMDb") or imdb_id
            except Exception:
                pass

        display_title = title or details.get("Name") or ""
        position, duration = canonical_local_resume(
            imdb_id, media_type, season, episode, display_title, item_id
        )
        if start_position not in (None, ""):
            position = float(start_position or 0)
            duration = float(start_duration or duration or 0)

        stream = jf.stream_url(item_id)
        item = xbmcgui.ListItem(label=display_title, path=stream)
        tag = item.getVideoInfoTag()
        tag.setTitle(literal_label(display_title))
        tag.setUniqueID(item_id, "jellyfin")
        if imdb_id:
            tag.setUniqueID(imdb_id, "imdb")
        if item_type == "Episode":
            tag.setSeason(season)
            tag.setEpisode(episode)
            if details.get("SeriesName"):
                tag.setTvShowTitle(details.get("SeriesName"))

        if position > 0 and duration > 0:
            tag.setResumePoint(position, duration)

        item.setProperty("IsPlayable", "true")
        active_media.save({
            "source": "local",
            "jellyfin_item_id": str(item_id),
            "imdb_id": str(imdb_id),
            "media_type": media_type,
            "season": season,
            "episode": episode,
            "title": display_title,
            "show_title": details.get("SeriesName") or "",
        })
        playback_session.save(
            "jellyfin",
            imdb_id,
            media_type,
            season,
            episode,
            display_title,
            jellyfin_item_id=item_id,
            requested_start_position=position,
            requested_duration=duration,
            # Initial Player.Open consumes the ResumePoint. Never classify
            # this handoff as "live" or PlaybackMonitor will visibly re-seek.
            resume_mode="resume" if position > 0 else "native",
        )
        xbmcplugin.setResolvedUrl(HANDLE, True, item)
    except Exception as exc:
        xbmc.log(f"[Apollo Media] Headless local playback failed: {exc}", xbmc.LOGERROR)
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())

def play_jellyfin_native(item_id, title):
    """Enter local playback through Kodi's normal PlayMedia decision path."""
    if not item_id:
        notify("Playback failed: missing Jellyfin item", xbmcgui.NOTIFICATION_ERROR)
        return
    target = plugin_url(action="play_jellyfin", item_id=item_id, title=title)
    xbmc.executebuiltin(f"PlayMedia({target})")




def settings():
    ADDON.openSettings()
    finish_action()


def link_torbox():
    link_account(ADDON)
    finish_action()


def detect_device_compatibility():
    resolution_options = [
        ("2160p / 4K", {
            "allow_2160p": True,
            "allow_1080p": True,
            "allow_720p": True,
            "allow_480p": True,
        }),
        ("1080p", {
            "allow_2160p": False,
            "allow_1080p": True,
            "allow_720p": True,
            "allow_480p": True,
        }),
        ("720p", {
            "allow_2160p": False,
            "allow_1080p": False,
            "allow_720p": True,
            "allow_480p": True,
        }),
        ("480p", {
            "allow_2160p": False,
            "allow_1080p": False,
            "allow_720p": False,
            "allow_480p": True,
        }),
    ]

    current_resolution = 1
    if ADDON.getSettingBool("allow_2160p"):
        current_resolution = 0
    elif not ADDON.getSettingBool("allow_1080p") and ADDON.getSettingBool("allow_720p"):
        current_resolution = 2
    elif not ADDON.getSettingBool("allow_720p"):
        current_resolution = 3

    resolution_choice = xbmcgui.Dialog().select(
        "Apollo Media - Display Resolution",
        [label for label, _ in resolution_options],
        preselect=current_resolution,
    )
    if resolution_choice < 0:
        return

    description, detected = detect_compatibility(ADDON)

    option_groups = [
        (
            "HDR",
            [
                ("allow_sdr", "SDR"),
                ("allow_hdr10", "HDR10"),
                ("allow_hdr10plus", "HDR10+"),
                ("allow_dolby_vision", "Dolby Vision"),
                ("allow_hlg", "HLG"),
            ],
        ),
        (
            "Video Codecs",
            [
                ("allow_h264", "H.264 / AVC"),
                ("allow_hevc", "H.265 / HEVC"),
                ("allow_av1", "AV1"),
                ("allow_mpeg2", "MPEG-2"),
                ("allow_vc1", "VC-1"),
            ],
        ),
        (
            "Audio Formats",
            [
                ("allow_aac", "AAC"),
                ("allow_ac3", "Dolby Digital / AC-3"),
                ("allow_eac3", "Dolby Digital Plus / E-AC-3"),
                ("allow_dts", "DTS"),
                ("allow_dtshd", "DTS-HD"),
                ("allow_truehd", "Dolby TrueHD"),
                ("allow_unknown", "Unknown Audio Formats"),
            ],
        ),
    ]

    display_rows = []
    option_row_to_setting = {}
    preselected = []

    for group_name, group_options in option_groups:
        # Kodi's native multi-select has no disabled/header row type.
        # These rows are visual separators only and are ignored on save.
        display_rows.append(f"----- {group_name} -----")

        for setting_id, label in group_options:
            display_index = len(display_rows)
            display_rows.append(label)
            option_row_to_setting[display_index] = setting_id
            if detected.get(setting_id, False):
                preselected.append(display_index)

    selected = xbmcgui.Dialog().multiselect(
        "Apollo Media - Review Device Compatibility",
        display_rows,
        preselect=preselected,
    )
    if selected is None:
        return

    selected_settings = {
        option_row_to_setting[index]
        for index in selected
        if index in option_row_to_setting
    }

    # Apply chosen resolution only after the review dialog is submitted.
    for setting_id, value in resolution_options[resolution_choice][1].items():
        ADDON.setSettingBool(setting_id, value)

    # Apply the reviewed auto-detection results. Separator/header rows are
    # deliberately ignored even if Kodi allows them to receive focus/checks.
    all_review_settings = {
        setting_id
        for _, group_options in option_groups
        for setting_id, _ in group_options
    }
    for setting_id in all_review_settings:
        ADDON.setSettingBool(setting_id, setting_id in selected_settings)

    resolution_label = resolution_options[resolution_choice][0]
    detected_device = f"{description} • Resolution: {resolution_label}"
    ADDON.setSettingString("detected_device", detected_device)

    enabled = len(selected_settings) + sum(
        1 for value in resolution_options[resolution_choice][1].values() if value
    )

    xbmcgui.Dialog().ok(
        "Apollo Media - Device Profile",
        f"Saved: {detected_device}\n\n"
        f"Enabled {enabled} compatibility options.",
    )
    finish_action()


def remove_continue_item(source, item_id="", imdb_id="", season=0, episode=0, headless=False):
    """
    Remove one identity from Continue Watching.

    Card/HA removal is headless and must never refresh or navigate Kodi's GUI.
    Kodi's own context-menu action keeps the historical Container.Refresh.
    """
    season = int(season or 0)
    episode = int(episode or 0)
    headless = bool(headless)

    try:
        if imdb_id:
            progress.remove(imdb_id, season, episode)
            source_session.clear_resume(imdb_id, season, episode)
        if source == "jellyfin" and item_id:
            jellyfin().clear_resume(item_id)

        if not headless:
            notify("Removed from Continue Watching", xbmcgui.NOTIFICATION_INFO)
            xbmc.executebuiltin("Container.Refresh")
    except Exception as exc:
        xbmc.log(f"[Apollo Media] Remove Continue Watching failed: {exc}", xbmc.LOGERROR)
        if not headless:
            notify(
                f"Could not remove from Continue Watching: {exc}",
                xbmcgui.NOTIFICATION_ERROR,
            )



def remote_remove_continue(source, item_id="", imdb_id="", season=0, episode=0):
    """JSON-RPC Files.GetDirectory action used by the HA card.

    This route deliberately returns an empty directory result after changing
    progress state. It never refreshes/updates/activates a Kodi GUI container.
    """
    remove_continue_item(source, item_id, imdb_id, season, episode, headless=True)
    xbmcplugin.setContent(HANDLE, "files")
    xbmcplugin.endOfDirectory(HANDLE, succeeded=True, updateListing=False, cacheToDisc=False)

def route():
    values = parameters()
    action = values.get("action", "home")
    routes = {
        "home": home,
        "connect_jellyfin": connect_jellyfin,
        "trending": trending,
        "trending_series": trending_tv,
        "popular": popular,
        "search": search,
        "library": library,
        "popular_series": popular_tv,
        "search_series": search_tv,
        "series_library": series_library,
        "continue": continue_watching,
        "settings": settings,
        "link_torbox": link_torbox,
        "detect_compatibility": detect_device_compatibility,
    }
    if action == "play_resolved":
        play_resolved(values.get("source", ""), values.get("item_id", ""), values.get("imdb", ""),
                      values.get("media_type", "movie"), values.get("season", "0"), values.get("episode", "0"),
                      values.get("title", ""), values.get("resume_item_id", ""), values.get("resume_mode", ""))
    elif action == "play_discovery":
        play_discovery(values.get("imdb", ""), values.get("title", ""))
    elif action == "play_jellyfin":
        play_jellyfin(
            values.get("item_id", ""),
            values.get("title", ""),
            values.get("start_over", "") == "1",
        )
    elif action == "play_jellyfin_native":
        play_jellyfin_native(values.get("item_id", ""), values.get("title", ""))
    elif action == "remote_play_jellyfin":
        raw_start = values.get("start_position")
        raw_duration = values.get("start_duration")
        remote_play_jellyfin(
            values.get("item_id", ""),
            values.get("title", ""),
            values.get("resume_mode", ""),
            float(raw_start) if raw_start not in (None, "") else None,
            float(raw_duration) if raw_duration not in (None, "") else None,
        )
    elif action == "discovery_seasons":
        discovery_seasons(
            values.get("imdb", ""),
            values.get("title", ""),
            values.get("native_local", "") == "1",
        )
    elif action == "discovery_episodes":
        discovery_episodes(
            values.get("imdb", ""),
            values.get("season", "0"),
            values.get("native_local", "") == "1",
        )
    elif action == "seasons":
        show_seasons(
            values.get("series_id", ""),
            values.get("imdb", ""),
            values.get("title", ""),
            values.get("native_local", "") == "1",
        )
    elif action == "episodes":
        show_episodes(
            values.get("series_id", ""),
            values.get("season_id", ""),
            values.get("imdb", ""),
            values.get("title", ""),
            values.get("native_local", "") == "1",
        )
    elif action == "remove_continue":
        remove_continue_item(
            values.get("source", ""),
            values.get("item_id", ""),
            values.get("imdb", ""),
            values.get("season", "0"),
            values.get("episode", "0"),
            values.get("headless", "") == "1",
        )
    elif action == "remote_remove_continue":
        remote_remove_continue(
            values.get("source", ""),
            values.get("item_id", ""),
            values.get("imdb", ""),
            values.get("season", "0"),
            values.get("episode", "0"),
        )
    elif action == "play_external_resolved_prompt":
        play_external_resolved_prompt(
            values.get("imdb", ""),
            values.get("media_type", "movie"),
            values.get("season"),
            values.get("episode"),
            values.get("title", ""),
            values.get("resume_item_id", ""),
        )
    elif action == "play_external_prompt":
        play_external_prompt(
            values.get("imdb", ""),
            values.get("media_type", "movie"),
            values.get("season"),
            values.get("episode"),
            values.get("title", ""),
            values.get("resume_item_id", ""),
        )
    elif action == "play_external":
        raw_start = values.get("start_position")
        raw_duration = values.get("start_duration")
        play_external(
            values.get("imdb", ""),
            values.get("media_type", "movie"),
            values.get("season"),
            values.get("episode"),
            values.get("title", ""),
            values.get("resume_item_id", ""),
            float(raw_start) if raw_start not in (None, "") else None,
            float(raw_duration) if raw_duration not in (None, "") else None,
            values.get("resume_mode", ""),
        )
    elif action == "remote_catalog":
        remote_movie_catalog(values.get("list_type", "popular"), values.get("query", ""))
    elif action == "remote_media_list":
        remote_media_list(
            values.get("list_type", "popular"), values.get("query", ""),
            int(values.get("offset", "0") or 0),
            min(100, max(1, int(values.get("limit", "60") or 60))),
            values.get("sort_by", "SortName"), values.get("sort_order", "Ascending"),
        )
    elif action == "choose_external":
        choose_external(
            values.get("imdb", ""),
            values.get("media_type", "movie"),
            values.get("season"),
            values.get("episode"),
            values.get("title", ""),
            values.get("resume_item_id", ""),
        )
    elif action == "remote_stream_list":
        remote_stream_list(
            values.get("imdb", ""),
            values.get("media_type", "movie"),
            values.get("season"),
            values.get("episode"),
            values.get("title", ""),
            values.get("resume_item_id", ""),
        )
    elif action == "play_session_stream":
        raw_start = values.get("start_position")
        raw_duration = values.get("start_duration")
        play_session_stream(
            values.get("index", "0"),
            float(raw_start) if raw_start not in (None, "") else None,
            float(raw_duration) if raw_duration not in (None, "") else None,
            values.get("resume_mode", ""),
        )
    elif action == "manual_flag_stream":
        manual_flag_stream(values.get("index", "0"))
    elif action == "manual_unflag_stream":
        manual_unflag_stream(values.get("index", "0"))
    elif action == "current_stream_info":
        current_stream_info()
    elif action == "try_next":
        play_next_stream()
    elif action == "flag_current":
        flag_current(values.get("reason", ""))
    elif action == "show_on_tv":
        show_on_tv(values.get("path", ""))
    else:
        routes.get(action, home)()


if __name__ == "__main__":
    route()
