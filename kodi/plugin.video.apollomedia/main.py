import sys
import time
from datetime import date, datetime
from urllib.parse import parse_qsl, urlencode

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

from resources.lib import ams, source_session
from resources.lib.sources import find_streams
from resources.lib.compatibility import detect as detect_compatibility, profile as compatibility_profile
from resources.lib.torbox import link_account
from resources.lib.stream_dialog import StreamChooserDialog

ADDON = xbmcaddon.Addon()
HANDLE = int(sys.argv[1])
BASE = sys.argv[0]

_RUN_STARTED = time.monotonic()

def _perf(label, started):
    xbmc.log(f"[ApolloPerf] {label}: {time.monotonic()-started:.3f}s", xbmc.LOGINFO)



def params():
    raw = sys.argv[2][1:] if len(sys.argv) > 2 and sys.argv[2] else ""
    return dict(parse_qsl(raw))


def url(action, **values):
    payload = {"action": action}
    payload.update({k: v for k, v in values.items() if v is not None})
    return BASE + "?" + urlencode(payload)


def end(content=None):
    if content:
        xbmcplugin.setContent(HANDLE, content)
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)


def notify(text, level=xbmcgui.NOTIFICATION_INFO):
    xbmcgui.Dialog().notification("Apollo Media", text, level, 5000)


def art(row):
    result = {}
    poster = str(row.get("poster_url") or row.get("poster") or "")
    fanart = str(row.get("backdrop_url") or row.get("fanart") or "")
    if poster:
        result.update({"poster": poster, "thumb": poster})
    if fanart:
        result["fanart"] = fanart
    return result


def apply_common(item, row, title, imdb_id=""):
    tag = item.getVideoInfoTag()
    tag.setTitle(str(title or "Unknown"))
    if imdb_id:
        tag.setUniqueID(str(imdb_id), "imdb")
    plot = str(row.get("overview") or row.get("plot") or "")
    if plot:
        tag.setPlot(plot)
    year = row.get("year")
    if year:
        try:
            tag.setYear(int(str(year)[:4]))
        except Exception:
            pass
    artwork = art(row)
    if artwork:
        item.setArt(artwork)


def folder(label, target, row=None, imdb_id=""):
    item = xbmcgui.ListItem(label=str(label))
    item.setProperty("IsPlayable", "false")
    if row:
        apply_common(item, row, label, imdb_id)
    xbmcplugin.addDirectoryItem(HANDLE, target, item, True)


def action_item(label, target):
    item = xbmcgui.ListItem(label=str(label))
    item.setProperty("IsPlayable", "false")
    xbmcplugin.addDirectoryItem(HANDLE, target, item, False)


def playable_media(row, media_type, label="", season=0, episode=0, show_title="", progress=None):
    """Render a single canonical Apollo playable item.

    Normal activation is always remote playback. Local availability is a
    capability exposed through the context menu.
    """
    title = str(row.get("title") or label or "Unknown")
    display_label = str(label or title)
    imdb = str(row.get("imdb_id") or "").strip()

    item = xbmcgui.ListItem(label=display_label)
    item.setProperty("IsPlayable", "true")
    apply_common(item, row, title, imdb)
    # Preserve Apollo's explicit presentation label after Kodi metadata.
    item.setLabel(display_label)

    tag = item.getVideoInfoTag()
    if int(episode or 0) > 0:
        tag.setSeason(int(season or 0))
        tag.setEpisode(int(episode or 0))
        if show_title:
            tag.setTvShowTitle(str(show_title))
        # Keep Apollo's episode presentation annotation visible in Estuary.
        tag.setTitle(display_label)
        air_date = str(row.get("air_date") or "").strip()
        if air_date:
            try:
                tag.setFirstAired(air_date[:10])
            except Exception as exc:
                xbmc.log(f"[Apollo] first-aired metadata failed: {exc}", xbmc.LOGWARNING)

    # Always initialize Kodi state explicitly so a recycled/cached ListItem
    # cannot leak watched/resume metadata from another directory rendering.
    tag.setPlaycount(0)
    tag.setResumePoint(0.0, 0.0)

    try:
        if progress is None:
            position, duration, watched = ams.progress_for(
                ADDON, row, season=season, episode=episode
            )
        else:
            position = max(0.0, float(progress[0] or 0))
            duration = max(0.0, float(progress[1] or 0))
            watched = bool(progress[2]) if len(progress) > 2 else False

        if watched:
            tag.setPlaycount(1)
        elif position > 0 and duration > 0:
            tag.setResumePoint(position, duration)
    except Exception as exc:
        xbmc.log(f"[Apollo] progress rendering failed: {exc}", xbmc.LOGWARNING)

    item.addContextMenuItems(
        _play_context(
            row,
            media_type,
            season=season,
            episode=episode,
            title=title,
            show_title=show_title,
        )
    )
    xbmcplugin.addDirectoryItem(
        HANDLE,
        url(
            "play_remote",
            **_remote_params(
                row,
                media_type,
                season=season,
                episode=episode,
                title=title,
                show_title=show_title,
            ),
        ),
        item,
        False,
    )

def home():
    folder("Library Movies", url("library_movies"))
    folder("Library Shows", url("library_shows"))
    folder("Continue Watching", url("continue"))
    folder("Popular Movies", url("discovery", mode="popular", media_type="movie"))
    folder("Popular Shows", url("discovery", mode="popular", media_type="show"))
    folder("Trending Movies", url("discovery", mode="trending", media_type="movie"))
    folder("Trending Shows", url("discovery", mode="trending", media_type="show"))
    folder("Search Movies", url("search", media_type="movie"))
    folder("Search Shows", url("search", media_type="show"))
    item = xbmcgui.ListItem(label="Settings")
    xbmcplugin.addDirectoryItem(HANDLE, url("settings"), item, False)
    end("files")


def library_movies():
    try:
        rows = ams.media(ADDON, "movie", available_locally=True)
        rows.sort(key=lambda x: str(x.get("title") or "").casefold())
        for row in rows:
            playable_media(row, "movie")
    except Exception as exc:
        notify(f"AMS movie library failed: {exc}", xbmcgui.NOTIFICATION_ERROR)
    end("movies")


def _local_episodes(imdb="", season=None):
    return ams.media(
        ADDON,
        "episode",
        available_locally=True,
        imdb_id=imdb,
        season=season,
    )


def _show_groups(rows):
    grouped = {}
    for row in rows:
        imdb = str(row.get("imdb_id") or "").strip()
        if not imdb:
            continue
        current = grouped.get(imdb)
        if current is None:
            grouped[imdb] = row
            continue
        score = sum(bool(current.get(k)) for k in ("series_title", "poster_url", "backdrop_url", "overview"))
        new_score = sum(bool(row.get(k)) for k in ("series_title", "poster_url", "backdrop_url", "overview"))
        if new_score > score:
            grouped[imdb] = row
    return grouped


def library_shows():
    try:
        rows = ams.media(ADDON, "show", available_locally=True)
        rows.sort(key=lambda row: str(row.get("title") or "").casefold())
        for row in rows:
            imdb = str(row.get("imdb_id") or "").strip()
            if not imdb:
                continue
            title = str(row.get("title") or "Unknown")
            tmdb = str(row.get("tmdb_id") or "").strip()
            target = url("discovery_show", tmdb=tmdb, imdb=imdb, title=title) if tmdb else url("show", imdb=imdb, title=title)
            folder(title, target, row, imdb)
    except Exception as exc:
        notify(f"AMS show library failed: {exc}", xbmcgui.NOTIFICATION_ERROR)
    end("tvshows")


def show(imdb, title):
    try:
        rows = _local_episodes(imdb=imdb)
        seasons = sorted({int(row.get("season") or 0) for row in rows})
        for season in seasons:
            label = "Specials" if season == 0 else f"Season {season}"
            sample = next((r for r in rows if int(r.get("season") or 0) == season), {})
            folder(label, url("season", imdb=imdb, season=season, title=title), sample, imdb)
    except Exception as exc:
        notify(f"AMS seasons failed: {exc}", xbmcgui.NOTIFICATION_ERROR)
    end("seasons")


def season(imdb, season_number, title):
    try:
        rows = _local_episodes(imdb=imdb, season=season_number)
        rows.sort(key=lambda r:int(r.get("episode") or 0))
        for row in rows:
            episode = int(row.get("episode") or 0)
            ep_title = str(row.get("title") or f"Episode {episode}")
            playable_media(
                row,
                "series",
                label=f"{episode}. {ep_title}",
                season=season_number,
                episode=episode,
                show_title=title,
            )
    except Exception as exc:
        notify(f"AMS episodes failed: {exc}",xbmcgui.NOTIFICATION_ERROR)
    end("episodes")

def continue_watching():
    try:
        rows = ams.continue_watching(ADDON)
        for row in rows:
            season = int(row.get("season") or 0)
            episode = int(row.get("episode") or 0)
            title = str(row.get("title") or "Unknown")
            show_title = str(row.get("series_title") or row.get("show_title") or "")
            if episode > 0:
                label = f"{show_title or title} — S{season:02d}E{episode:02d} — {title}"
                playable_media(
                    row,
                    "series",
                    label=label,
                    season=season,
                    episode=episode,
                    show_title=show_title,
                    progress=(
                        row.get("position_seconds") or 0,
                        row.get("duration_seconds") or 0,
                        False,
                    ),
                )
            else:
                playable_media(
                    row,
                    "movie",
                    progress=(
                        row.get("position_seconds") or 0,
                        row.get("duration_seconds") or 0,
                        False,
                    ),
                )
    except Exception as exc:
        notify(f"AMS Continue Watching failed: {exc}", xbmcgui.NOTIFICATION_ERROR)
    end("movies")

def _canonical_detail_target(row):
    media_type = str(row.get("media_type") or "").lower()
    if media_type == "movie":
        return url(
            "movie",
            media_id=row.get("media_id") or row.get("id"),
            imdb=row.get("imdb_id"),
            title=row.get("title") or "Movie",
        )
    return url(
        "discovery_show",
        media_id=row.get("media_id") or row.get("id"),
        imdb=row.get("imdb_id"),
        tmdb=row.get("tmdb_id"),
        title=row.get("title") or "Show",
        available_locally="1" if row.get("available_locally") else "0",
    )


def discovery_list(mode, media_type, page=1):
    page=max(1,int(page or 1))
    try:
        rows=ams.discovery(ADDON,mode,media_type,page=page)
        for row in rows:
            title=str(row.get("title") or "Unknown")
            if media_type=="movie":
                playable_media(row, "movie")
            else:
                folder(title,_canonical_detail_target(row),row,str(row.get("imdb_id") or ""))
        if len(rows) >= 20:
            folder("More Results",url("discovery",mode=mode,media_type=media_type,page=page+1))
    except Exception as exc:
        notify(f"AMS discovery failed: {exc}",xbmcgui.NOTIFICATION_ERROR)
    end("movies" if media_type=="movie" else "tvshows")

def search(media_type, query="", page=1):
    page=max(1,int(page or 1))
    query = str(query or "").strip() or xbmcgui.Dialog().input(
        "Search Movies" if media_type == "movie" else "Search Shows",
        type=xbmcgui.INPUT_ALPHANUM,
    ).strip()
    if not query:
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False, cacheToDisc=False)
        return
    try:
        rows = ams.discovery(ADDON, "search", media_type, query, page=page)
        for row in rows:
            title = str(row.get("title") or "Unknown")
            if media_type=="movie":
                playable_media(row, "movie")
            else:
                folder(title,_canonical_detail_target(row),row,str(row.get("imdb_id") or ""))
        if len(rows) >= 20:
            folder("More Results",url("search",media_type=media_type,query=query,page=page+1))
    except Exception as exc:
        notify(f"AMS search failed: {exc}", xbmcgui.NOTIFICATION_ERROR)
    end("movies" if media_type == "movie" else "tvshows")


def discovery_show(p):
    tmdb = str(p.get("tmdb") or "").strip()
    if not tmdb:
        notify("Show is missing its TMDB identity", xbmcgui.NOTIFICATION_ERROR)
        end("seasons"); return
    try:
        details = ams.discovery_show(ADDON, tmdb)
        title = str(details.get("title") or p.get("title") or "Show")
        imdb = str(details.get("imdb_id") or p.get("imdb") or "")
        for row in details.get("seasons") or []:
            season_number = int(row.get("season") or 0)
            label = str(row.get("title") or ("Specials" if season_number == 0 else f"Season {season_number}"))
            season_row = {
                "title": label,
                "year": details.get("year"),
                "poster_url": row.get("poster_url") or details.get("poster_url"),
                "backdrop_url": details.get("backdrop_url"),
                "overview": row.get("overview") or details.get("overview"),
            }
            folder(label, url("discovery_season", tmdb=tmdb, imdb=imdb,
                              season=season_number, title=title), season_row, imdb)
    except Exception as exc:
        notify(f"AMS seasons failed: {exc}", xbmcgui.NOTIFICATION_ERROR)
    end("seasons")

def _episode_air_label(air_date):
    value=str(air_date or "").strip()
    if not value: return ""
    try: target=date.fromisoformat(value[:10])
    except Exception: return ""
    today=date.today()
    if target <= today: return ""
    # Keep the episode title neutral and make the future-airing status
    # visually distinct in Kodi's list row. Gold stays readable against
    # both Estuary's normal dark list background and selected blue row.
    return "[COLOR gold]Airing on " + target.strftime("%b %d").replace(" 0"," ") + "[/COLOR]"

def discovery_season(p):
    tmdb = str(p.get("tmdb") or "").strip()
    season_number = int(p.get("season") or 0)
    title = str(p.get("title") or "Show")
    try:
        result = ams.discovery_season(ADDON, tmdb, season_number)
        show_row = result.get("show") or {}
        show_title = str(show_row.get("title") or title)
        for row in result.get("episodes") or []:
            episode = int(row.get("episode") or 0)
            ep_title = str(row.get("title") or f"Episode {episode}")
            air_label=_episode_air_label(row.get("air_date"))
            label=f"{episode}. {ep_title}" + (f"  •  {air_label}" if air_label else "")
            playable_media(row, "series", label=label,
                           season=season_number, episode=episode,
                           show_title=show_title)
    except Exception as exc:
        notify(f"AMS episodes failed: {exc}", xbmcgui.NOTIFICATION_ERROR)
    end("episodes")


def _bool_setting(name, default=True):
    try:
        return ADDON.getSettingBool(name)
    except Exception:
        value=str(ADDON.getSettingString(name) or "").strip().lower()
        return default if not value else value in ("true","1","yes","on")


def _remote_profile():
    result = compatibility_profile(ADDON)
    for key in ("provider_priority","preferred_languages","allowed_languages","excluded_languages"):
        result[key] = ADDON.getSettingString(key)
    return result

def _providers():
    return [name for name in ("comet","torrentio","debridio") if _bool_setting("provider_"+name, name!="debridio")]


def _remote_params(row, media_type, season=0, episode=0, title="", show_title=""):
    return dict(
        media_id=str(row.get("media_id") or row.get("id") or ""),
        canonical_id=str(row.get("canonical_id") or ""),
        imdb=str(row.get("imdb_id") or ""),
        tmdb=str(row.get("tmdb_id") or ""),
        media_type=media_type,
        season=int(season or 0),
        episode=int(episode or 0),
        title=str(title or row.get("title") or "Unknown"),
        show_title=str(show_title or row.get("series_title") or row.get("show_title") or ""),
        year=str(row.get("year") or ""),
        overview=str(row.get("overview") or ""),
        poster_url=str(row.get("poster_url") or ""),
        backdrop_url=str(row.get("backdrop_url") or ""),
        expected_duration=int(row.get("expected_duration_seconds") or (float(row.get("runtime") or 0)*60) or 0),
    )


def _play_context(row, media_type, season=0, episode=0, title="", show_title=""):
    remote = _remote_params(
        row,
        media_type,
        season=season,
        episode=episode,
        title=title,
        show_title=show_title,
    )
    actions = [
        ("Pick Stream Manually", f"RunPlugin({url('play_remote_choose', **remote)})")
    ]
    media_id = str(row.get("media_id") or row.get("id") or "")
    if int(episode or 0) > 0:
        actions.append((
            "Go to Season",
            "Container.Update(" + url(
                "go_to_season",
                imdb=str(row.get("imdb_id") or ""),
                series_tmdb=str(row.get("series_tmdb_id") or ""),
                season=int(season or 0),
                title=str(show_title or row.get("series_title") or row.get("show_title") or ""),
            ) + ")",
        ))
        actions.append((
            "Go to Series",
            "Container.Update(" + url(
                "go_to_series",
                imdb=str(row.get("imdb_id") or ""),
                series_tmdb=str(row.get("series_tmdb_id") or ""),
                title=str(show_title or row.get("series_title") or row.get("show_title") or ""),
            ) + ")",
        ))
    if row.get("available_locally") and media_id:
        actions.insert(
            0,
            (
                "Play Locally",
                f"RunPlugin({url('play_local', media_id=media_id, canonical_id=row.get('canonical_id') or '', imdb=row.get('imdb_id') or '', media_type=media_type, season=int(season or 0), episode=int(episode or 0), title=title or row.get('title') or 'Unknown', show_title=show_title or row.get('series_title') or row.get('show_title') or '')})",
            ),
        )
    if source_session.load():
        actions.extend([
            ("Current Stream Info", f"RunPlugin({url('current_stream_info')})"),
            ("Try Next Stream", f"RunPlugin({url('try_next')})"),
        ("TEST: Fail Current Stream Start", f"RunPlugin({url('test_fail_current_start')})"),
            ("Flag Current Stream", f"RunPlugin({url('flag_current')})"),
        ])
    return actions


def _stream_candidates(p, cached_only=True):
    imdb = str(p.get("imdb") or "").strip()
    if not imdb:
        media_id = str(p.get("media_id") or "").strip()
        if media_id:
            identity = ams.resolve_playback_identity(ADDON, media_id)
            imdb = str(identity.get("imdb_id") or "").strip()
            if imdb:
                p["imdb"] = imdb
            canonical = str(identity.get("canonical_id") or "").strip()
            if canonical:
                p["canonical_id"] = canonical
            tmdb = str(identity.get("tmdb_id") or "").strip()
            if tmdb:
                p["tmdb"] = tmdb
    if not imdb:
        raise RuntimeError("Remote playback requires an IMDb identity")

    media_type = (
        "series"
        if str(p.get("media_type") or "") in ("show", "series", "episode")
        or int(p.get("episode") or 0) > 0
        else "movie"
    )
    providers = _providers()
    if not providers:
        raise RuntimeError("Enable at least one remote source provider")

    return find_streams(
        ADDON.getSettingString("torbox_token"),
        providers,
        imdb,
        media_type,
        int(p.get("season") or 0) if media_type == "series" else None,
        int(p.get("episode") or 0) if media_type == "series" else None,
        _remote_profile(),
        ADDON.getSettingString("debridio_url"),
        cached_only=bool(cached_only),
    )


def _session_params(session):
    session = session or {}
    return {
        "imdb": str(session.get("imdb_id") or ""),
        "media_type": str(session.get("media_type") or "movie"),
        "season": int(session.get("season") or 0),
        "episode": int(session.get("episode") or 0),
        "title": str(session.get("title") or "Remote"),
        "canonical_id": str(session.get("canonical_id") or ""),
        "media_id": str(session.get("media_id") or ""),
        "show_title": str(session.get("show_title") or ""),
        "tmdb": str(session.get("tmdb") or ""),
        "year": str(session.get("year") or ""),
        "overview": str(session.get("overview") or ""),
        "poster_url": str(session.get("poster_url") or ""),
        "backdrop_url": str(session.get("backdrop_url") or ""),
        "expected_duration": int(session.get("expected_duration") or 0),
    }


def _resolve_remote(stream, p):
    source_session.begin_attempt()
    item = xbmcgui.ListItem(path=stream.url if hasattr(stream, "url") else str(stream.get("url") or ""))
    provider_raw = stream.provider if hasattr(stream, "provider") else stream.get("provider")
    title_raw = stream.title if hasattr(stream, "title") else stream.get("title")
    provider = str(provider_raw or "remote").strip().title()

    item.setProperty("ApolloPlaybackMode", "remote")
    item.setProperty("ApolloPlaybackProvider", provider)
    item.setProperty("ApolloPlaybackSource", f"Remote • {provider}")

    runtime = xbmcgui.Window(10000)
    runtime.setProperty("ApolloPlaybackMode", "remote")
    runtime.setProperty("ApolloPlaybackProvider", provider)
    runtime.setProperty("ApolloPlaybackSource", f"Remote • {provider}")

    canonical_id = str(p.get("canonical_id") or "").strip()
    media_id = str(p.get("media_id") or "").strip()
    if canonical_id:
        runtime.setProperty("ApolloCanonicalId", canonical_id)
    if media_id:
        runtime.setProperty("ApolloMediaId", media_id)
    expected_duration=int(float(p.get("expected_duration") or 0))
    if expected_duration > 0:
        runtime.setProperty("ApolloExpectedDuration",str(expected_duration))
    else:
        runtime.clearProperty("ApolloExpectedDuration")
    for key,value in (
        ("ApolloSeriesTitle",p.get("show_title")),
        ("ApolloTmdbId",p.get("tmdb")),
        ("ApolloYear",p.get("year")),
        ("ApolloOverview",p.get("overview")),
        ("ApolloPosterUrl",p.get("poster_url")),
        ("ApolloBackdropUrl",p.get("backdrop_url")),
    ):
        value=str(value or "").strip()
        if value: runtime.setProperty(key,value)
        else: runtime.clearProperty(key)

    tag = item.getVideoInfoTag()
    tag.setTitle(str(p.get("title") or title_raw or "Remote"))
    if canonical_id:
        try:
            tag.setUniqueID(canonical_id, "apollo")
        except Exception:
            pass
    imdb = str(p.get("imdb") or "")
    if imdb:
        tag.setUniqueID(imdb, "imdb")

    season = int(p.get("season") or 0)
    episode = int(p.get("episode") or 0)
    if episode > 0:
        tag.setSeason(season)
        tag.setEpisode(episode)
        show_title = str(p.get("show_title") or "")
        if show_title:
            tag.setTvShowTitle(show_title)

    session = source_session.load() or {}
    resume_mode = str(session.get("resume_mode") or "beginning")
    if resume_mode == "fixed":
        position = max(0.0, float(session.get("resume_position") or 0))
        if position > 0:
            # Apollo owns the one resume decision for the whole source session.
            # StartOffset carries it to fallback URLs without another Kodi
            # native resume prompt.
            item.setProperty("StartOffset", str(position))

    item.setProperty("IsPlayable", "true")
    xbmcplugin.setResolvedUrl(HANDLE, True, item)


def _save_source_session(streams, p):
    imdb = str(p.get("imdb") or "")
    season = int(p.get("season") or 0)
    episode = int(p.get("episode") or 0)
    resume_position, resume_duration = ams.resume(ADDON, imdb, season, episode)
    resume_mode = "beginning"
    if resume_position > 0 and resume_duration > 0:
        total_seconds = max(0, int(resume_position))
        resume_label = f"{total_seconds // 60}:{total_seconds % 60:02d}"
        if xbmcgui.Dialog().yesno(
            "Apollo Media",
            f"Resume from {resume_label}?",
            nolabel="Play from beginning",
            yeslabel="Resume",
        ):
            resume_mode = "fixed"
        else:
            resume_position, resume_duration = 0.0, 0.0

    session = source_session.save(
        streams,
        imdb,
        "series" if episode > 0 or str(p.get("media_type") or "") in ("series", "episode", "show") else "movie",
        season,
        episode,
        str(p.get("title") or "Remote"),
        resume_position=resume_position,
        resume_duration=resume_duration,
        resume_mode=resume_mode,
    )
    # Preserve canonical Apollo identity alongside the proven session format.
    session["canonical_id"] = str(p.get("canonical_id") or "")
    session["media_id"] = str(p.get("media_id") or "")
    session["show_title"] = str(p.get("show_title") or "")
    session["tmdb"] = str(p.get("tmdb") or "")
    session["year"] = str(p.get("year") or "")
    session["overview"] = str(p.get("overview") or "")
    session["poster_url"] = str(p.get("poster_url") or "")
    session["backdrop_url"] = str(p.get("backdrop_url") or "")
    session["expected_duration"] = int(float(p.get("expected_duration") or 0))
    try:
        import json, os, xbmcvfs
        directory = xbmcvfs.translatePath("special://profile/addon_data/plugin.video.apollomedia")
        with open(os.path.join(directory, "source_session.json"), "w", encoding="utf-8") as handle:
            json.dump(session, handle)
    except Exception:
        pass
    return session


def _choose_stream_dialog():
    while True:
        session = source_session.load() or {}
        streams = session.get("streams") or []
        flags = source_session.flags()
        flags_by_url = {
            str(entry.get("url") or ""): entry
            for entry in flags
            if str(entry.get("url") or "")
        }
        rows = [
            {
                "index": index,
                "stream": stream,
                "flagged": source_session.is_flagged(index),
            }
            for index, stream in enumerate(streams)
        ]
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
            return None
        action, original_index = result
        if action == "play":
            _, stream = source_session.select(original_index)
            return stream
        if action == "flag":
            manual_flag_stream(original_index)
            continue
        if action == "unflag":
            manual_unflag_stream(original_index)
            continue


def play_remote(p, choose=False):
    try:
        cached_only=str(p.get("cached_only") or "1") != "0"
        streams=_stream_candidates(p,cached_only=cached_only)
        if not streams and cached_only:
            if xbmcgui.Dialog().yesno(
                "Apollo Media",
                "No cached streams were found.",
                "Search uncached sources?",
                nolabel="Cancel",
                yeslabel="Search Uncached",
            ):
                retry=dict(p); retry["cached_only"]="0"
                streams=_stream_candidates(retry,cached_only=False)
                p=retry
        if not streams:
            notify("No compatible remote streams found", xbmcgui.NOTIFICATION_WARNING)
            xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
            return

        session = _save_source_session(streams, p)
        stream = source_session.current()

        if choose:
            stream = _choose_stream_dialog()
            if not stream:
                return
            # Manual picker is launched from a context-menu RunPlugin action.
            # setResolvedUrl() cannot start playback from that non-playable
            # invocation, so hand the selected session stream to Kodi as a
            # fresh playable plugin URL.
            selected = source_session.load() or {}
            index = int(selected.get("index") or 0)
            xbmc.executebuiltin(
                "PlayMedia(" + url("play_session_stream", index=index) + ")"
            )
            return

        if not stream:
            notify("All compatible streams are flagged", xbmcgui.NOTIFICATION_WARNING)
            xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
            return

        _resolve_remote(stream, p)
    except Exception as exc:
        notify(f"Remote playback failed: {exc}", xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())


def go_to_season(p):
    imdb=str(p.get("imdb") or "").strip()
    tmdb=str(p.get("series_tmdb") or "").strip()
    title=str(p.get("title") or "Show")
    season_number=int(p.get("season") or 0)
    try:
        if not tmdb and imdb:
            identity=ams.series_identity(ADDON,imdb)
            tmdb=str(identity.get("tmdb_id") or "").strip()
            title=str(identity.get("title") or title)
        if tmdb:
            discovery_season({"tmdb":tmdb,"imdb":imdb,"season":season_number,"title":title})
            return
        if imdb:
            season(imdb,season_number,title)
            return
        raise RuntimeError("Season identity is unavailable")
    except Exception as exc:
        notify(f"Unable to open season: {exc}",xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.endOfDirectory(HANDLE,succeeded=False,cacheToDisc=False)

def go_to_series(p):
    imdb = str(p.get("imdb") or "").strip()
    tmdb = str(p.get("series_tmdb") or "").strip()
    title = str(p.get("title") or "Show")
    try:
        if not tmdb and imdb:
            identity = ams.series_identity(ADDON, imdb)
            tmdb = str(identity.get("tmdb_id") or "").strip()
            title = str(identity.get("title") or title)
        if tmdb:
            discovery_show({"tmdb": tmdb, "imdb": imdb, "title": title})
            return
        if imdb:
            show(imdb, title)
            return
        raise RuntimeError("Series identity is unavailable")
    except Exception as exc:
        notify(f"Unable to open series: {exc}", xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False, cacheToDisc=False)


def current_stream_info():
    session = source_session.load() or {}
    stream = source_session.current()
    if not stream:
        notify("There is no active Apollo stream", xbmcgui.NOTIFICATION_INFO)
        return
    streams = session.get("streams") or []
    index = int(session.get("index") if session.get("index") is not None else -1)
    provider = str(stream.get("provider") or "Unknown provider")
    title = str(stream.get("title") or stream.get("description") or "Unknown stream")
    flag = source_session.flag_for_url(stream.get("url") or "")
    flagged = "No"
    if flag:
        flagged = str(flag.get("reason") or "flagged").replace("_", " ").title()
    xbmcgui.Dialog().ok(
        f"Current Stream • {provider} • {index + 1}/{len(streams)}",
        f"Flagged: {flagged}\n\n{title}",
    )


def test_fail_current_start():
    session = source_session.load() or {}
    if not source_session.current():
        notify("No Apollo stream session is available", xbmcgui.NOTIFICATION_WARNING)
        return
    source_session.begin_attempt(int(session.get("index") or 0), timeout=12.0, force_fail=True)
    notify("Test armed: current stream will fail before confirmation", xbmcgui.NOTIFICATION_INFO)
    xbmc.Player().stop()
    xbmc.executebuiltin("PlayMedia(" + url("play_session_stream", index=int(session.get("index") or 0)) + ")")


def try_next():
    session, stream = source_session.advance()
    if not stream:
        notify("No more compatible streams are available", xbmcgui.NOTIFICATION_WARNING)
        return
    p = _session_params(session)
    xbmc.Player().stop()
    xbmc.executebuiltin(
        "PlayMedia(" + url(
            "play_session_stream",
            index=int(session.get("index") or 0),
        ) + ")"
    )


def play_session_stream(p):
    session = source_session.load() or {}
    try:
        index = int(p.get("index") or session.get("index") or 0)
    except Exception:
        index = 0
    _, stream = source_session.select(index)
    if not stream:
        notify("Apollo stream session is no longer available", xbmcgui.NOTIFICATION_WARNING)
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return
    _resolve_remote(stream, _session_params(session))


def _flag_reason():
    reasons = [
        ("bad_stream", "Bad stream / playback failure"),
        ("wrong_content", "Wrong content"),
        ("wrong_language", "Wrong language"),
    ]
    choice = xbmcgui.Dialog().select(
        "What is wrong with this stream?",
        [label for _, label in reasons],
    )
    return reasons[choice][0] if 0 <= choice < len(reasons) else ""


def flag_current():
    stream = source_session.current()
    if not stream:
        notify("There is no active Apollo stream to flag", xbmcgui.NOTIFICATION_WARNING)
        return
    reason = _flag_reason()
    if not reason:
        return
    source_session.flag(reason)
    notify("Stream flagged", xbmcgui.NOTIFICATION_INFO)


def manual_flag_stream(index):
    reason = _flag_reason()
    if not reason:
        return
    if source_session.flag_index(index, reason):
        notify("Stream flagged", xbmcgui.NOTIFICATION_INFO)


def manual_unflag_stream(index):
    if source_session.unflag_index(index):
        notify("Stream unflagged", xbmcgui.NOTIFICATION_INFO)
    else:
        notify("Stream was not flagged", xbmcgui.NOTIFICATION_INFO)


def detect_device_compatibility():
    description, values = detect_compatibility(ADDON)
    labels = []
    keys = [
        ("allow_2160p", "2160p / 4K"),
        ("allow_1080p", "1080p"),
        ("allow_720p", "720p"),
        ("allow_480p", "480p / SD"),
    ]
    selected = []
    for i, (key, label) in enumerate(keys):
        labels.append(label)
        if values.get(key, True):
            selected.append(i)
    chosen = xbmcgui.Dialog().multiselect(
        f"Device Compatibility • {description}",
        labels,
        preselect=selected,
    )
    if chosen is None:
        return
    chosen = set(chosen)
    for i, (key, _) in enumerate(keys):
        ADDON.setSettingBool(key, i in chosen)
    for key, value in values.items():
        if key not in dict(keys):
            ADDON.setSettingBool(key, bool(value))
    try:
        ADDON.setSettingString("detected_device", description)
    except Exception:
        pass
    notify("Device compatibility updated", xbmcgui.NOTIFICATION_INFO)


def link_torbox():
    link_account(ADDON)

def play_local(p):
    media_id = str(p.get("media_id") or "")
    canonical_id = str(p.get("canonical_id") or "")
    imdb = str(p.get("imdb") or "")
    media_type = str(p.get("media_type") or "movie")
    season = int(p.get("season") or 0)
    episode = int(p.get("episode") or 0)
    title = str(p.get("title") or "Unknown")
    show_title = str(p.get("show_title") or "")
    try:
        decision = ams.playback_resolution(ADDON, media_id)
        if str(decision.get("mode") or "") != "local":
            raise RuntimeError(f"AMS did not return local playback: {decision}")
        path = str(decision.get("playback_path") or "").strip()
        if not path:
            raise RuntimeError("AMS returned no playback path")
        # Handoff the exact AMS identity to the playback monitor.  A global
        # Kodi window property survives plugin -> resolved URL -> player,
        # unlike arbitrary ListItem properties on some Kodi builds.
        runtime = xbmcgui.Window(10000)
        runtime.setProperty("ApolloMediaId", media_id)
        runtime.setProperty("ApolloCanonicalId", canonical_id)

        item = xbmcgui.ListItem(label=title, path=path)
        tag = item.getVideoInfoTag()
        tag.setTitle(title)
        if canonical_id:
            try:
                tag.setUniqueID(canonical_id, "apollo")
            except Exception:
                pass
        if imdb:
            tag.setUniqueID(imdb, "imdb")
        if episode:
            tag.setSeason(season)
            tag.setEpisode(episode)
            if show_title:
                tag.setTvShowTitle(show_title)
        position, duration = ams.resume(ADDON, imdb, season, episode)
        if position > 0 and duration > 0:
            tag.setResumePoint(position, duration)
        item.setProperty("IsPlayable", "true")
        item.setProperty("ApolloPlaybackMode","local")
        item.setProperty("ApolloPlaybackProvider","AMS")
        item.setProperty("ApolloPlaybackSource","Local • AMS")
        runtime.setProperty("ApolloPlaybackMode","local")
        runtime.setProperty("ApolloPlaybackProvider","AMS")
        runtime.setProperty("ApolloPlaybackSource","Local • AMS")
        xbmcplugin.setResolvedUrl(HANDLE, True, item)
    except Exception as exc:
        notify(f"Local playback failed: {exc}", xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())


def settings():
    ADDON.openSettings()
    xbmcplugin.endOfDirectory(HANDLE, succeeded=False, cacheToDisc=False)


def dispatch():
    p = params()
    action = p.get("action") or "home"
    if action == "home":
        home()
    elif action == "library_movies":
        library_movies()
    elif action == "library_shows":
        library_shows()
    elif action == "show":
        show(p.get("imdb"), p.get("title") or "Show")
    elif action == "season":
        season(p.get("imdb"), int(p.get("season") or 0), p.get("title") or "Show")
    elif action == "continue":
        continue_watching()
    elif action == "discovery":
        discovery_list(p.get("mode") or "popular",p.get("media_type") or "movie",int(p.get("page") or 1))
    elif action == "search":
        search(p.get("media_type") or "movie",p.get("query") or "",int(p.get("page") or 1))
    elif action == "discovery_show":
        discovery_show(p)
    elif action == "discovery_season":
        discovery_season(p)
    elif action == "go_to_season":
        go_to_season(p)
    elif action == "go_to_series":
        go_to_series(p)
    elif action == "play_remote":
        play_remote(p,False)
    elif action == "play_remote_choose":
        play_remote(p,True)
    elif action == "play_session_stream":
        play_session_stream(p)
    elif action == "current_stream_info":
        current_stream_info()
    elif action == "try_next":
        try_next()
    elif action == "test_fail_current_start":
        test_fail_current_start()
    elif action == "flag_current":
        flag_current()
    elif action == "detect_compatibility":
        detect_device_compatibility()
    elif action == "link_torbox":
        link_torbox()
    elif action == "play_local":
        play_local(p)
    elif action == "settings":
        settings()
    else:
        notify(f"Unknown Apollo route: {action}", xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False, cacheToDisc=False)


try:
    dispatch()
finally:
    _perf("plugin invocation total", _RUN_STARTED)
