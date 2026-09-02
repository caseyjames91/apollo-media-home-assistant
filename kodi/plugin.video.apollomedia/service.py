import threading
import time
import xbmc
import xbmcaddon
import xbmcgui

from resources.lib import ams, source_session

ADDON = xbmcaddon.Addon()
_lock = threading.Lock()
_in_flight = False
_retry_lock = threading.Lock()
_retry_in_flight = False


def report_async(canonical_id, imdb_id, media_type, season, episode, title, position, duration,
                 series_title="", tmdb_id="", year=None, overview="", poster_url="", backdrop_url=""):
    global _in_flight
    if not canonical_id or duration <= 0:
        return
    with _lock:
        if _in_flight:
            return
        _in_flight = True

    def worker():
        global _in_flight
        try:
            ams.report_progress(
                ADDON, canonical_id, imdb_id, media_type, season, episode,
                title, position, duration,
                series_title=series_title, tmdb_id=tmdb_id, year=year,
                overview=overview, poster_url=poster_url, backdrop_url=backdrop_url,
            )
        except Exception as exc:
            xbmc.log(f"[Apollo Media 0.10] AMS progress report failed: {exc}", xbmc.LOGWARNING)
        finally:
            with _lock:
                _in_flight = False

    threading.Thread(target=worker, name="ApolloAMSProgress", daemon=True).start()


def _plugin_url(action, **values):
    from urllib.parse import urlencode
    payload={"action":action}; payload.update(values)
    return "plugin://plugin.video.apollomedia/?" + urlencode(payload)


def _retry_failed_attempt(reason):
    global _retry_in_flight
    with _retry_lock:
        if _retry_in_flight: return
        _retry_in_flight=True
    try:
        session,stream=source_session.fail_attempt(reason)
        if not stream:
            xbmcgui.Dialog().notification("Apollo Media","No more compatible streams are available",xbmcgui.NOTIFICATION_WARNING,5000)
            return
        index=int((session or {}).get("index") or 0)
        xbmc.log(f"[ApolloFallback] retry index={index} reason={reason}",xbmc.LOGINFO)
        xbmc.executebuiltin("PlayMedia("+_plugin_url("play_session_stream",index=index)+")")
    finally:
        with _retry_lock: _retry_in_flight=False


class MonitorPlayer(xbmc.Player):
    def __init__(self):
        super().__init__()
        self.clear()

    def clear(self):
        self.canonical_id = ""
        self.imdb = ""
        self.media_type = "movie"
        self.season = 0
        self.episode = 0
        self.title = ""
        self.last_position = 0.0
        self.last_duration = 0.0
        self.expected_duration = 0.0
        self.series_title = ""
        self.tmdb_id = ""
        self.year = None
        self.overview = ""
        self.poster_url = ""
        self.backdrop_url = ""

    def identify(self):
        try:
            tag = self.getVideoInfoTag()
            runtime = xbmcgui.Window(10000)
            self.canonical_id = str(
                runtime.getProperty("ApolloCanonicalId")
                or tag.getUniqueID("apollo")
                or ""
            )
            self.imdb = str(tag.getUniqueID("imdb") or "")
            # Consume the handoff once playback has inherited it so stale
            # identity cannot leak into unrelated playback.
            runtime.clearProperty("ApolloCanonicalId")
            runtime.clearProperty("ApolloMediaId")
            self.season = max(0, int(tag.getSeason()))
            self.episode = max(0, int(tag.getEpisode()))
            self.media_type = "series" if self.episode > 0 else "movie"
            self.title = str(tag.getTitle() or "Unknown")
            try:
                self.expected_duration=max(0.0,float(runtime.getProperty("ApolloExpectedDuration") or 0))
            except Exception:
                self.expected_duration=0.0
            runtime.clearProperty("ApolloExpectedDuration")
            self.series_title=str(runtime.getProperty("ApolloSeriesTitle") or tag.getTVShowTitle() or "")
            self.tmdb_id=str(runtime.getProperty("ApolloTmdbId") or "")
            try: self.year=int(runtime.getProperty("ApolloYear") or 0) or None
            except Exception: self.year=None
            self.overview=str(runtime.getProperty("ApolloOverview") or "")
            self.poster_url=str(runtime.getProperty("ApolloPosterUrl") or "")
            self.backdrop_url=str(runtime.getProperty("ApolloBackdropUrl") or "")
            for key in ("ApolloSeriesTitle","ApolloTmdbId","ApolloYear","ApolloOverview","ApolloPosterUrl","ApolloBackdropUrl"):
                runtime.clearProperty(key)
        except Exception:
            self.clear()

    def sample(self):
        try:
            self.last_position = max(0.0, float(self.getTime()))
        except Exception:
            pass
        try:
            self.last_duration = max(0.0, float(self.getTotalTime()))
        except Exception:
            pass
        return self.last_position, self.last_duration

    def duration_is_implausible(self):
        if self.expected_duration <= 0:
            return False
        _, duration = self.sample()
        if duration <= 0:
            return False
        ratio = duration / self.expected_duration
        return ratio < 0.50 or ratio > 1.75

    def emit(self):
        if not self.canonical_id:
            return
        position, duration = self.sample()
        if position < 10.0:
            return
        if self.expected_duration > 0 and duration > 0:
            ratio=duration/self.expected_duration
            if ratio < 0.50 or ratio > 1.75:
                xbmc.log(f"[ApolloProgress] ignoring implausible duration actual={duration:.1f}s expected={self.expected_duration:.1f}s",xbmc.LOGWARNING)
                return
        if duration > 0:
            report_duration=self.expected_duration if self.expected_duration > 0 else duration
            report_async(
                self.canonical_id, self.imdb, self.media_type, self.season, self.episode,
                self.title, position, report_duration,
                self.series_title, self.tmdb_id, self.year,
                self.overview, self.poster_url, self.backdrop_url,
            )

    def onAVStarted(self):
        attempts=source_session.attempt_state()
        if attempts.get("state")=="requested" and attempts.get("force_fail"):
            xbmc.log("[ApolloFallback] synthetic startup failure",xbmc.LOGINFO)
            self.stop(); _retry_failed_attempt("synthetic_test"); return
        source_session.confirm_attempt()
        self.identify()
        self.sample()
        if self.duration_is_implausible():
            xbmc.log(
                f"[ApolloFallback] implausible opened duration actual={self.last_duration:.1f}s "
                f"expected={self.expected_duration:.1f}s",
                xbmc.LOGWARNING,
            )
            self.stop()
            _retry_failed_attempt("implausible_duration")
            self.clear()
            return
        try:
            source=xbmcgui.Window(10000).getProperty("ApolloPlaybackSource")
            if source:
                xbmcgui.Dialog().notification("Apollo Media",source,xbmcgui.NOTIFICATION_INFO,5000)
        except Exception:
            pass

    def onPlayBackError(self):
        if source_session.attempt_state().get("state")=="requested":
            xbmc.log("[ApolloFallback] Kodi error before confirmation",xbmc.LOGWARNING)
            _retry_failed_attempt("kodi_playback_error")

    def onPlayBackPaused(self):
        self.emit()

    def onPlayBackResumed(self):
        self.emit()

    def onPlayBackSeek(self, time, seekOffset):
        self.emit()

    def _clear_playback_source(self):
        try:
            runtime=xbmcgui.Window(10000)
            runtime.clearProperty("ApolloPlaybackMode")
            runtime.clearProperty("ApolloPlaybackProvider")
            runtime.clearProperty("ApolloPlaybackSource")
        except Exception:
            pass

    def onPlayBackStopped(self):
        self.emit()
        self._clear_playback_source()
        self.clear()

    def onPlayBackEnded(self):
        self.emit()
        self._clear_playback_source()
        self.clear()


monitor = xbmc.Monitor()
player = MonitorPlayer()
ticks = 0
while not monitor.abortRequested():
    if monitor.waitForAbort(1):
        break
    attempts=source_session.attempt_state()
    if attempts.get("state")=="requested":
        try: deadline=float(attempts.get("deadline") or 0)
        except Exception: deadline=0
        if deadline and time.time() >= deadline:
            xbmc.log("[ApolloFallback] startup confirmation timed out",xbmc.LOGWARNING)
            _retry_failed_attempt("startup_timeout")

    if player.canonical_id and player.isPlayingVideo():
        player.sample()
        if player.duration_is_implausible():
            xbmc.log(
                f"[ApolloFallback] implausible opened duration actual={player.last_duration:.1f}s "
                f"expected={player.expected_duration:.1f}s",
                xbmc.LOGWARNING,
            )
            player.stop()
            _retry_failed_attempt("implausible_duration")
            player.clear()
            ticks = 0
            continue
        ticks += 1
        if ticks >= 10:
            player.emit()
            ticks = 0
    else:
        ticks = 0
