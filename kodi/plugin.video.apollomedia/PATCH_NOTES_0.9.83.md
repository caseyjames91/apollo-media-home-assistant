# Apollo Media 0.9.83

- Continue Watching in both Kodi UI and headless/card routes now prefers AMS as the profile-scoped authority.
- Kodi imports its existing local Apollo progress into AMS using original timestamps, then consumes the merged AMS timeline.
- Kodi playback reports progress to AMS asynchronously so network latency cannot block player callbacks.
- Added AMS URL/profile settings to Kodi; default direct endpoint is `http://homeassistant.local:8099`.
- Card AMS artwork is fetched through authenticated HA ingress into stable browser blob URLs, preventing poster flash/disappearance when ingress sessions rotate.
- Card refresh is local when AMS is enabled and no longer launches the shared HA media refresh script or shared Continue Watching refresh sensor.
- Existing playback, native resume, source switching, stream picker, and per-card `player_entity` paths are unchanged.
