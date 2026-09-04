import threading

import xbmc
import xbmcaddon
import xbmcgui

from resources.lib import ams, source_session
from resources.lib.playback_validation import duration_valid


ADDON = xbmcaddon.Addon()

_lock = threading.Lock()
_in_flight = False


def report_async(
    canonical_id,
    imdb_id,
    media_type,
    season,
    episode,
    title,
    position,
    duration,
):
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
                ADDON,
                canonical_id,
                imdb_id,
                media_type,
                season,
                episode,
                title,
                position,
                duration,
            )
        except Exception as exc:
            xbmc.log(
                f"[Apollo Media 0.10] AMS progress report failed: {exc}",
                xbmc.LOGWARNING,
            )
        finally:
            with _lock:
                _in_flight = False

    threading.Thread(
        target=worker,
        name="ApolloAMSProgress",
        daemon=True,
    ).start()


class MonitorPlayer(xbmc.Player):
    def __init__(self):
        super().__init__()
        self.generation = 0
        self.clear()

    def clear(self):
        # Invalidate any outstanding asynchronous identity lookup.
        self.generation += 1

        self.canonical_id = ""
        self.media_id = ""
        self.imdb = ""
        self.media_type = "movie"
        self.season = 0
        self.episode = 0
        self.title = ""

        self.playback_mode = ""
        self.expected_duration = 0.0
        self.identity_ready = False
        self.validated = False
        self.suppress_progress = False
        self.rejection_started = False

        self.last_position = 0.0
        self.last_duration = 0.0

    def identify(self):
        self.clear()

        try:
            tag = self.getVideoInfoTag()
            runtime = xbmcgui.Window(10000)

            self.canonical_id = str(
                runtime.getProperty("ApolloCanonicalId")
                or tag.getUniqueID("apollo")
                or ""
            )
            self.media_id = str(runtime.getProperty("ApolloMediaId") or "")
            self.playback_mode = str(
                runtime.getProperty("ApolloPlaybackMode") or ""
            ).strip().lower()

            self.imdb = str(tag.getUniqueID("imdb") or "")
            self.season = max(0, int(tag.getSeason()))
            self.episode = max(0, int(tag.getEpisode()))
            self.media_type = "series" if self.episode > 0 else "movie"
            self.title = str(tag.getTitle() or "Unknown")

            # Consume the handoff once playback has inherited it so stale
            # identity cannot leak into unrelated playback.
            runtime.clearProperty("ApolloCanonicalId")
            runtime.clearProperty("ApolloMediaId")

            # Only remote provider playback needs source validation.
            if self.playback_mode == "remote":
                self._load_expected_runtime()
            else:
                self.validated = True
                self.identity_ready = True

        except Exception:
            self.clear()

    def _load_expected_runtime(self):
        token = self.generation
        media_id = self.media_id

        if not media_id:
            # No AMS media identity is available. The validator will use its
            # conservative short-duration fallback.
            self.identity_ready = True
            return

        def worker():
            expected = 0.0

            try:
                identity = ams.media_item(ADDON, media_id)
                expected = max(
                    0.0,
                    float(identity.get("runtime_seconds") or 0),
                )
            except Exception as exc:
                xbmc.log(
                    f"[Apollo Media 0.10] Playback validation lookup failed: {exc}",
                    xbmc.LOGWARNING,
                )

            # Playback may have changed while AMS was answering.
            if self.generation != token:
                return

            self.expected_duration = expected
            self.identity_ready = True

        threading.Thread(
            target=worker,
            name="ApolloPlaybackIdentity",
            daemon=True,
        ).start()

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

    def _validate_remote(self, allow_fallback=False):
        if self.playback_mode != "remote":
            return True

        if self.validated:
            return True

        if self.suppress_progress or self.rejection_started:
            return False

        if not self.identity_ready and not allow_fallback:
            return None

        _, duration = self.sample()
        expected = self.expected_duration if self.identity_ready else 0.0
        decision = duration_valid(duration, expected)

        if decision is None:
            return None

        if decision:
            self.validated = True
            return True

        self._reject_current_stream()
        return False

    def _reject_current_stream(self):
        if self.rejection_started:
            return

        # This must happen before Player.stop(). Kodi may synchronously issue
        # onPlayBackStopped(), and rejected playback must never reach AMS.
        self.rejection_started = True
        self.suppress_progress = True

        try:
            source_session.flag("bad_stream")
            session, stream = source_session.advance()
        except Exception as exc:
            xbmc.log(
                f"[Apollo Media 0.10] Failed to quarantine bad stream: {exc}",
                xbmc.LOGERROR,
            )
            session, stream = None, None

        try:
            xbmcgui.Dialog().notification(
                "Apollo Media",
                "Bad stream detected • trying next source",
                xbmcgui.NOTIFICATION_WARNING,
                4000,
            )
        except Exception:
            pass

        try:
            self.stop()
        except Exception:
            pass

        if not stream or not session:
            try:
                xbmcgui.Dialog().notification(
                    "Apollo Media",
                    "No more compatible streams are available",
                    xbmcgui.NOTIFICATION_WARNING,
                    5000,
                )
            except Exception:
                pass
            return

        index = int(session.get("index") or 0)
        xbmc.executebuiltin(
            "PlayMedia("
            f"plugin://plugin.video.apollomedia/?action=play_session_stream&index={index}"
            ")"
        )

    def emit(self):
        if not self.canonical_id or self.suppress_progress:
            return

        if self.playback_mode == "remote":
            decision = self._validate_remote()
            if decision is not True:
                return

        position, duration = self.sample()
        if duration > 0:
            report_async(
                self.canonical_id,
                self.imdb,
                self.media_type,
                self.season,
                self.episode,
                self.title,
                position,
                duration,
            )

    def onAVStarted(self):
        self.identify()
        self.sample()

        try:
            source = xbmcgui.Window(10000).getProperty("ApolloPlaybackSource")
            if source:
                xbmcgui.Dialog().notification(
                    "Apollo Media",
                    source,
                    xbmcgui.NOTIFICATION_INFO,
                    5000,
                )
        except Exception:
            pass

    def onPlayBackPaused(self):
        self.emit()

    def onPlayBackResumed(self):
        self.emit()

    def onPlayBackSeek(self, time, seekOffset):
        self.emit()

    def _clear_playback_source(self):
        try:
            runtime = xbmcgui.Window(10000)
            runtime.clearProperty("ApolloPlaybackMode")
            runtime.clearProperty("ApolloPlaybackProvider")
            runtime.clearProperty("ApolloPlaybackSource")
        except Exception:
            pass

    def onPlayBackStopped(self):
        if not self.suppress_progress:
            self.emit()

        self._clear_playback_source()
        self.clear()

    def onPlayBackEnded(self):
        # If a tiny error clip reaches EOF before AMS answered, the fallback
        # rule can still reject it without ever reporting progress.
        if (
            self.playback_mode == "remote"
            and not self.validated
            and not self.suppress_progress
        ):
            self._validate_remote(allow_fallback=True)

        if not self.suppress_progress:
            self.emit()

        self._clear_playback_source()
        self.clear()


monitor = xbmc.Monitor()
player = MonitorPlayer()
ticks = 0

while not monitor.abortRequested():
    if monitor.waitForAbort(1):
        break

    if player.canonical_id and player.isPlayingVideo():
        player.sample()

        if player.playback_mode == "remote" and not player.validated:
            player._validate_remote()

        ticks += 1
        if ticks >= 10:
            player.emit()
            ticks = 0
    else:
        ticks = 0
