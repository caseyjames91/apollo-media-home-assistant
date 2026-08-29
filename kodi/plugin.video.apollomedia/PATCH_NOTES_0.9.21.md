# Apollo Media 0.9.21

- Removes the experimental `Clear Progress` action from 0.9.20.
- Testing confirmed Kodi's built-in `Reset resume position` is what clears
  the native resume bookmark/indicator shown on plugin items.
- Apollo will not duplicate Kodi's native reset control.
- Unified Apollo/Jellyfin progress work from 0.9.18-0.9.19 remains in place
  for continued testing.
- `Remove from Continue Watching` still clears Apollo/Jellyfin/source-session
  state, but it is intentionally not presented as a Kodi bookmark reset.
