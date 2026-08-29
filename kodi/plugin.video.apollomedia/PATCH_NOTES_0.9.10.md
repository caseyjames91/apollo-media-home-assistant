# Apollo Media 0.9.10

- Clean rollback to the 0.9.8 codebase.
- Removes the ineffective 0.9.9 Continue Watching label experiment.
- Keeps independent provider toggles for Comet, Torrentio and Debridio.
- Keeps Debridio configured-addon URL support.
- Keeps all previously working Jellyfin, playback, source ranking, flagging,
  Try Next Stream, compatibility and settings behavior.
- No new Continue Watching presentation logic is included in this build.
- Continue Watching will be recalculated from the actual renderer/path that
  produces Kodi's current `S01E01 • Episode Name` display.
