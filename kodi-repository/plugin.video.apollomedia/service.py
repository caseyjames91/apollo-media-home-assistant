import base64
import json
import threading
from urllib.parse import urlencode

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



def _episode_art(row):
    poster = str(row.get("poster_url") or row.get("poster") or "")
    fanart = str(row.get("backdrop_url") or row.get("fanart") or "")
    return {
        "thumb": poster,
        "tvshow.clearart": "",
        "tvshow.clearlogo": "",
        "tvshow.fanart": fanart,
        "tvshow.landscape": fanart,
        "tvshow.poster": poster,
    }


def _episode_info(row, fallback=None):
    fallback = fallback or {}
    runtime = (
        row.get("expected_duration_seconds")
        or row.get("runtime_seconds")
        or row.get("duration_seconds")
        or fallback.get("runtime")
        or 0
    )
    return {
        "episodeid": str(row.get("media_id") or row.get("id") or row.get("canonical_id") or fallback.get("episodeid") or ""),
        "tvshowid": str(row.get("imdb_id") or fallback.get("tvshowid") or ""),
        "title": str(row.get("title") or fallback.get("title") or ""),
        "art": _episode_art(row) if row else (fallback.get("art") or {}),
        "season": int(row.get("season") or fallback.get("season") or 0),
        "episode": int(row.get("episode") or fallback.get("episode") or 0),
        "showtitle": str(row.get("series_title") or row.get("show_title") or fallback.get("showtitle") or ""),
        "plot": str(row.get("overview") or row.get("plot") or fallback.get("plot") or ""),
        "playcount": 1 if bool(row.get("watched")) else int(fallback.get("playcount") or 0),
        "rating": row.get("rating") or fallback.get("rating") or 0,
        "firstaired": str(row.get("air_date") or row.get("first_aired") or fallback.get("firstaired") or ""),
        "runtime": int(float(runtime or 0)),
    }


def _apollo_play_url(row):
    media_id = str(row.get("media_id") or row.get("id") or "").strip()
    if not media_id:
        return ""
    params = {
        "action": "play_remote",
        "media_id": media_id,
        "canonical_id": str(row.get("canonical_id") or ""),
        "imdb": str(row.get("imdb_id") or ""),
        "tmdb": str(row.get("tmdb_id") or ""),
        "media_type": "series",
        "season": int(row.get("season") or 0),
        "episode": int(row.get("episode") or 0),
        "title": str(row.get("title") or "Unknown"),
        "show_title": str(row.get("series_title") or row.get("show_title") or ""),
        "start_from_beginning": "1",
        "upnext_playback": "1",
    }
    return "plugin://plugin.video.apollomedia/?" + urlencode(params)


def _send_upnext(next_info):
    payload = base64.b64encode(
        json.dumps(next_info, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")
    request = {
        "jsonrpc": "2.0",
        "id": 0,
        "method": "JSONRPC.NotifyAll",
        "params": {
            "sender": "plugin.video.apollomedia.SIGNAL",
            "message": "upnext_data",
            "data": [payload],
        },
    }
    result = json.loads(xbmc.executeJSONRPC(json.dumps(request)))
    if result.get("result") != "OK":
        raise RuntimeError(f"Up Next signal failed: {result}")
    return True


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
        self.show_title = ""

        self.playback_mode = ""
        self.expected_duration = 0.0
        self.identity_ready = False
        self.validated = False
        self.suppress_progress = False
        self.rejection_started = False

        self.upnext_lookup_started = False
        self.upnext_sent = False

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
            try:
                self.show_title = str(tag.getTVShowTitle() or "")
            except Exception:
                self.show_title = ""

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
                self._maybe_prepare_upnext()

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

    def _maybe_prepare_upnext(self):
        if (
            self.upnext_lookup_started
            or self.upnext_sent
            or self.suppress_progress
            or not self.validated
            or self.episode <= 0
            or not self.media_id
        ):
            return

        self.upnext_lookup_started = True
        token = self.generation
        media_id = self.media_id
        current_fallback = {
            "episodeid": media_id or self.canonical_id,
            "tvshowid": self.imdb,
            "title": self.title,
            "art": {},
            "season": self.season,
            "episode": self.episode,
            "showtitle": self.show_title,
            "plot": "",
            "playcount": 0,
            "rating": 0,
            "firstaired": "",
            "runtime": int(self.last_duration or self.expected_duration or 0),
        }

        def worker():
            try:
                current = ams.media_item(ADDON, media_id) or {}
                next_row = ams.next_episode(ADDON, media_id) or {}
                if not next_row:
                    return
                play_url = _apollo_play_url(next_row)
                if not play_url:
                    return
                if self.generation != token or self.suppress_progress:
                    return
                next_info = {
                    "current_episode": _episode_info(current, fallback=current_fallback),
                    "next_episode": _episode_info(next_row),
                    "play_url": play_url,
                }
                _send_upnext(next_info)
                if self.generation == token:
                    self.upnext_sent = True
                    xbmc.log(
                        "[Apollo Media 0.10] Up Next prepared: "
                        f"S{int(next_row.get('season') or 0):02d}"
                        f"E{int(next_row.get('episode') or 0):02d} "
                        f"{next_row.get('title') or ''}",
                        xbmc.LOGINFO,
                    )
            except Exception as exc:
                if self.generation == token:
                    xbmc.log(
                        f"[Apollo Media 0.10] Up Next preparation failed: {exc}",
                        xbmc.LOGWARNING,
                    )

        threading.Thread(target=worker, name="ApolloUpNext", daemon=True).start()

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
            self._maybe_prepare_upnext()
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
            self._maybe_prepare_upnext()
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
        play_url = (
            "plugin://plugin.video.apollomedia/"
            f"?action=play_session_stream&index={index}"
        )
        xbmc.executebuiltin(f"PlayMedia({play_url},noresume)")

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
