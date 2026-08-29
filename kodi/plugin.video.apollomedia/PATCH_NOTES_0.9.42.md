# Apollo Media 0.9.42 — Local Activity Ordering and Chooser Playback

Continue Watching:
- Jellyfin-backed identities now use the newest activity timestamp known to either Jellyfin `UserData.LastPlayedDate` or Apollo `progress.updated`.
- Jellyfin remains authoritative for local metadata, playback and canonical resume behavior; Apollo activity affects ordering only.
- Apollo-only entries continue using `progress.updated`.
- Canonical IMDb + season + episode dedupe and existing fallbacks remain unchanged.

Remote stream chooser:
- Selecting Play now launches `PlayMedia(plugin://plugin.video.apollomedia/?action=play_session_stream&index=...)`.
- The dedicated playable route selects and resolves the exact source from Apollo's existing source session.
- No raw provider URL is passed through a context command.

No completion, removal, source ranking, provider, flag, resume, playback-route, chooser-style, or UI behavior changed outside these fixes.
