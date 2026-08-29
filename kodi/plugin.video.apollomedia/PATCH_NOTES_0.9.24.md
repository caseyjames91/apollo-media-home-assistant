# Apollo Media 0.9.24

- Fixes stale resume presentation on local movies shown in discovery lists.
- Popular Movies, Trending Movies and Search Movies now resolve and attach the
  same canonical local resume state used by Continue Watching before rendering.
- This prevents those rows from presenting an older Kodi-native bookmark when
  Jellyfin/Apollo already know a newer position.
- No playback routing, provider logic, ranking, or progress authority behavior changed.
