import re
import threading
from urllib.parse import parse_qs, urlparse

import xbmc
import xbmcaddon
import xbmcgui

from resources.lib.jellyfin import JellyfinClient
from resources.lib import progress, source_session, playback_session, ams


ADDON = xbmcaddon.Addon()
ITEM_PATTERN = re.compile(r"/Videos/([^/?]+)/stream", re.IGNORECASE)


def jellyfin():
    return JellyfinClient(
        ADDON.getSettingString("jellyfin_url"),
        ADDON.getSettingString("jellyfin_token"),
        ADDON.getSettingString("jellyfin_user_id"),
    )


_ams_report_lock = threading.Lock()
_ams_report_in_flight = False


def report_ams_progress_async(imdb_id, media_type, season, episode, title, position, duration, jellyfin_item_id=""):
    """Best-effort AMS report without ever blocking Kodi's player callbacks."""
    global _ams_report_in_flight
    ams_client = globals().get("ams")
    if ams_client is None or not imdb_id:
        return
    with _ams_report_lock:
        if _ams_report_in_flight:
            return
        _ams_report_in_flight = True

    def worker():
        global _ams_report_in_flight
        try:
            ams_client.report_progress(
                ADDON, imdb_id, media_type, season, episode, title, position, duration,
                jellyfin_item_id=jellyfin_item_id,
            )
        except Exception as exc:
            try:
                xbmc.log(f"[Apollo Media] AMS progress report failed: {exc}", xbmc.LOGWARNING)
            except Exception:
                pass
        finally:
            with _ams_report_lock:
                _ams_report_in_flight = False

    threading.Thread(target=worker, name="ApolloAMSProgress", daemon=True).start()


def jellyfin_identity(item_id):
    try:
        details = jellyfin().item(item_id) or {}
        item_type = details.get("Type") or "Movie"
        season = int(details.get("ParentIndexNumber") or 0)
        episode = int(details.get("IndexNumber") or 0)
        title = details.get("Name") or "Unknown"
        provider_ids = details.get("ProviderIds") or {}
        imdb_id = provider_ids.get("Imdb") or provider_ids.get("IMDb") or ""
        media_type = "movie"
        if item_type == "Episode":
            media_type = "series"
            series_id = details.get("SeriesId") or ""
            if series_id:
                series = jellyfin().item(series_id) or {}
                series_ids = series.get("ProviderIds") or {}
                imdb_id = series_ids.get("Imdb") or series_ids.get("IMDb") or imdb_id
        return imdb_id, media_type, season, episode, title
    except Exception as exc:
        xbmc.log(f"[Apollo Media] Jellyfin identity lookup failed: {exc}", xbmc.LOGWARNING)
        return "", "", 0, 0, ""


class PlaybackMonitor(xbmc.Player):
    def __init__(self):
        super().__init__()
        self.item_id = ""
        self.play_session_id = ""
        self.last_ticks = 0
        self.imdb_id = ""
        self.media_type = ""
        self.season = 0
        self.episode = 0
        self.title = ""
        self.last_duration = 0
        self.remote_jellyfin_item_id = ""
        self.playback_session = {}
        self.last_observed_position = 0.0
        self.last_observed_duration = 0.0

    def capture_position(self, fallback_position=None):
        """Capture live Kodi position without committing external state."""
        position = None
        try:
            position = max(0.0, float(self.getTime()))
        except Exception:
            pass

        if position is None and fallback_position is not None:
            try:
                raw = float(fallback_position)
                # Kodi's seek callback time is milliseconds.
                position = raw / 1000.0 if raw > 10000 else raw
            except Exception:
                position = None

        if position is None:
            position = float(self.last_observed_position or 0)

        try:
            duration = max(0.0, float(self.getTotalTime()))
        except Exception:
            duration = float(self.last_observed_duration or self.last_duration or 0)

        if duration > 0:
            self.last_observed_duration = duration
            self.last_duration = duration

        self.last_observed_position = max(0.0, position)
        self.last_ticks = max(0, int(self.last_observed_position * 10000000))

        if self.playback_session:
            try:
                playback_session.checkpoint(
                    self.last_observed_position,
                    self.last_observed_duration,
                )
            except Exception:
                pass

        return self.last_observed_position, self.last_observed_duration

    def position_ticks(self):
        self.capture_position()
        return self.last_ticks

    def report(self, event, paused=False):
        self.last_ticks = self.position_ticks()
        try:
            duration = max(0, float(self.getTotalTime()))
        except Exception:
            duration = self.last_duration
        self.last_duration = duration or self.last_duration
        position = self.last_ticks / 10000000

        jellyfin_item_id = (
            str((getattr(self, "playback_session", {}) or {}).get("jellyfin_item_id") or "")
            or self.item_id
            or self.remote_jellyfin_item_id
        )

        if jellyfin_item_id:
            # Keep Jellyfin's normal playback-session events for activity and
            # watched-state behavior.
            try:
                jellyfin().report_playback(
                    event,
                    jellyfin_item_id,
                    self.last_ticks,
                    paused,
                    self.play_session_id,
                )
            except Exception as exc:
                xbmc.log(
                    f"[Apollo Media] Jellyfin {event} report failed: {exc}",
                    xbmc.LOGWARNING,
                )

            # Persist resume explicitly as user data as well. This is the
            # authoritative resume write and does not depend on Jellyfin
            # accepting/retaining the playback-session event.
            if event in ("progress", "stop") and position >= 0:
                try:
                    jellyfin().set_resume(jellyfin_item_id, position)
                except Exception as exc:
                    xbmc.log(
                        f"[Apollo Media] Jellyfin resume sync failed: {exc}",
                        xbmc.LOGWARNING,
                    )

        # Apollo identity ledger mirrors the same position.
        if (self.imdb_id and self.last_ticks > 0 and self.last_duration > 0
                and (self.item_id or event != "start")):
            progress.save(
                self.imdb_id,
                self.media_type,
                self.season,
                self.episode,
                self.title,
                position,
                self.last_duration,
                jellyfin_synced_position=position if jellyfin_item_id else None,
            )
            ams_reporter = globals().get("report_ams_progress_async")
            if ams_reporter is not None:
                ams_reporter(
                    self.imdb_id, self.media_type, self.season, self.episode,
                    self.title, position, self.last_duration, jellyfin_item_id,
                )

    def onAVStarted(self):
        try:
            playing_file = self.getPlayingFile()
        except Exception:
            playing_file = ""

        # Read identity from Kodi first.
        match = ITEM_PATTERN.search(playing_file or "")
        kodi_item_id = match.group(1) if match else ""
        try:
            tag = self.getVideoInfoTag()
            if not kodi_item_id:
                kodi_item_id = tag.getUniqueID("jellyfin") or ""
            kodi_imdb = tag.getUniqueID("imdb") or ""
            kodi_season = max(0, int(tag.getSeason()))
            kodi_episode = max(0, int(tag.getEpisode()))
            kodi_title = tag.getTitle() or "Unknown"
        except Exception:
            kodi_imdb = ""
            kodi_season = 0
            kodi_episode = 0
            kodi_title = "Unknown"

        # A PlaybackSession is established by resolution BEFORE Kodi starts.
        # If it matches, it is authoritative for BOTH local and remote media.
        session = playback_session.load() or {}
        session_matches = playback_session.identity_matches(
            session, kodi_imdb, kodi_season, kodi_episode, kodi_item_id
        )

        self.playback_session = session if session_matches else {}
        if session_matches:
            self.item_id = str(session.get("jellyfin_item_id") or "")
            self.imdb_id = str(session.get("imdb_id") or kodi_imdb or "")
            self.media_type = str(session.get("media_type") or "movie")
            self.season = int(session.get("season") or 0)
            self.episode = int(session.get("episode") or 0)
            self.title = str(session.get("title") or kodi_title or "Unknown")
            self.remote_jellyfin_item_id = self.item_id if session.get("source") == "remote" else ""
        elif kodi_item_id:
            self.item_id = kodi_item_id
            (
                self.imdb_id,
                self.media_type,
                self.season,
                self.episode,
                self.title,
            ) = jellyfin_identity(self.item_id)
            self.remote_jellyfin_item_id = ""
        else:
            self.item_id = ""
            self.imdb_id = kodi_imdb
            self.season = kodi_season
            self.episode = kodi_episode
            self.media_type = "series" if self.season or self.episode else "movie"
            self.title = kodi_title
            self.remote_jellyfin_item_id = ""

            # Legacy direct-Kodi remote playback can still bind its Jellyfin
            # tracking target from source_session until those UI paths are retired.
            if self.imdb_id:
                try:
                    legacy = source_session.load() or {}
                    same_identity = (
                        str(legacy.get("imdb_id") or "").strip().lower()
                        == str(self.imdb_id or "").strip().lower()
                        and int(legacy.get("season") or 0) == self.season
                        and int(legacy.get("episode") or 0) == self.episode
                    )
                    if same_identity:
                        self.remote_jellyfin_item_id = str(
                            legacy.get("jellyfin_item_id") or ""
                        )
                except Exception:
                    pass

        query = parse_qs(urlparse(playing_file or "").query)
        self.play_session_id = (query.get("PlaySessionId") or [""])[0]
        self.last_ticks = 0
        self.last_duration = 0
        self.last_observed_position = 0.0
        self.last_observed_duration = 0.0

        # Initial Resume / Start Over is applied by Kodi's native Player.Open
        # adapter before visible playback. A post-AVStart absolute seek is only
        # correct for a live source handoff (Try Next / error failover), where
        # there is no new Player.Open resume decision to consume.
        if session_matches:
            requested = max(
                0.0, float(session.get("requested_start_position") or 0)
            )
            resume_mode = str(session.get("resume_mode") or "native")
            already_applied = bool(session.get("start_applied"))
            if requested > 0 and resume_mode == "live" and not already_applied:
                monitor = xbmc.Monitor()
                for _ in range(40):
                    if monitor.waitForAbort(0.25):
                        break
                    try:
                        if self.isPlayingVideo() and self.getTotalTime() > 0:
                            break
                    except Exception:
                        pass
                try:
                    self.seekTime(requested)
                    playback_session.mark_start_applied()
                except Exception as exc:
                    xbmc.log(
                        f"[Apollo Media] Canonical live handoff seek failed: {exc}",
                        xbmc.LOGWARNING,
                    )

        self.capture_position()
        self.report("start")

    def onPlayBackPaused(self):
        self.report("progress", paused=True)

    def onPlayBackResumed(self):
        self.report("progress")

    def onPlayBackSeek(self, time, seekOffset):
        self.capture_position(fallback_position=time)
        self.report("progress")

    def finish(self, completed=False):
        # getTime() may already be unavailable when Kodi delivers Stop.
        # capture_position therefore falls back to the last continuously
        # observed position, including the seek callback target.
        position, duration = self.capture_position()
        self.report("stop")

        position = self.last_observed_position
        duration = self.last_observed_duration or self.last_duration

        if self.imdb_id:
            if completed or (duration > 0 and position / duration >= 0.90):
                progress.remove(self.imdb_id, self.season, self.episode)

        if self.playback_session:
            try:
                playback_session.finish(
                    position, duration, completed=completed
                )
            except Exception:
                pass

        self.item_id = ""
        self.play_session_id = ""
        self.imdb_id = ""
        self.remote_jellyfin_item_id = ""
        self.playback_session = {}

    def onPlayBackStopped(self):
        self.finish()

    def onPlayBackEnded(self):
        self.finish(completed=True)

    def onPlayBackError(self):
        if not source_session.current():
            return

        source_session.flag("playback_error")
        session, stream = source_session.advance()
        if not session or not stream:
            xbmcgui.Dialog().notification(
                "Apollo Media", "No more compatible streams are available",
                xbmcgui.NOTIFICATION_WARNING, 5000,
            )
            return

        position, duration = self.capture_position()
        source_session.update_resume(position, duration, "live")
        playback_session.request_start(position, duration, "live")

        item = xbmcgui.ListItem(
            label=session.get("title") or "",
            path=stream.get("url") or "",
        )
        tag = item.getVideoInfoTag()
        tag.setTitle(session.get("title") or "")
        tag.setUniqueID(session.get("imdb_id") or "", "imdb")
        if session.get("media_type") == "series":
            tag.setSeason(int(session.get("season") or 0))
            tag.setEpisode(int(session.get("episode") or 0))
        if position > 0 and duration > 0:
            tag.setResumePoint(position, duration)
        item.setProperty("IsPlayable", "true")

        self.play(stream.get("url") or "", item)
        xbmcgui.Dialog().notification(
            "Apollo Media", "Trying the next stream", time=3000
        )


monitor = xbmc.Monitor()
player = PlaybackMonitor()
progress_seconds = 0
while not monitor.abortRequested():
    if monitor.waitForAbort(1):
        break
    if (player.item_id or player.imdb_id) and player.isPlayingVideo():
        player.capture_position()
        progress_seconds += 1
        if progress_seconds >= 10:
            player.report("progress")
            progress_seconds = 0
    else:
        progress_seconds = 0
