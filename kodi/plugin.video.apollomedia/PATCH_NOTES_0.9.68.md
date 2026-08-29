# Apollo Media 0.9.68 — Source Handoff State + Native Local Resume

## Remote -> Local handoff
- Reworked the local handoff to use Kodi `Player.Open` with `options.resume: true`.
- The current absolute playback position is carried as the resolved Jellyfin item's ResumePoint.
- The handoff is no longer marked `resume_mode=live`.
- PlaybackMonitor therefore does not perform the old visible post-AVStart seek when switching from remote to local.
- Remote -> local now uses the same native-initial-position principle that stabilized remote resume in 0.9.63.

## Active source state
- The card now invalidates stale Apollo Active Playback context whenever playback starts or changes source.
- Active context must be newer than the source-change request before it can drive the Now Playing UI.
- During local/remote transitions, the card also requires the returned active context to match the expected source type.
- This prevents a same-title stale local context from making remote playback look local, and vice versa.
- Try Next and Flag Stream also invalidate the active source context so provider/index/quality indicators refresh with the new source.

## Stream picker
- `Current` is now set only when the stored remote source is actually the file Kodi is currently playing.
- Switching to local playback no longer leaves an old remote source marked Current.
- The picker header and close button remain fixed while only the source list scrolls.
- Quality separators remain sticky inside the scrolling source list.

## Labels
- Local Now Playing now displays simply `LOCAL`.

## Preserved
- 0.9.63 playback/resume foundation.
- 0.9.64 refresh feedback.
- 0.9.65 stream picker / Try Next / Flag Stream framework.
- 0.9.66 remote-first card policy, quality/audio context, bidirectional source controls.
- 0.9.67 source-session regex import fix.
