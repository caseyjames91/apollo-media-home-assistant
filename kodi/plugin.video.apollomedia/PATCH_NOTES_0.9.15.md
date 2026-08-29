# Apollo Media 0.9.15

- Fixes `Play from Stream` doing nothing.
- Root cause: the context action used `RunPlugin(...)`, but `play_external()`
  returns playback through `xbmcplugin.setResolvedUrl()`, which requires Kodi
  to invoke the plugin URL as playable media.
- `Play from Stream` now uses `PlayMedia(plugin://...)`.
- `Choose Remote Stream` is unchanged.
- Normal local click remains Jellyfin-first.
- No changes to source search, ranking, compatibility scoring, or playback logic.
