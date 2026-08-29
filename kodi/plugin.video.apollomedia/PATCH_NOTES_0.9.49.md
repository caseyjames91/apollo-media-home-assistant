# Apollo Media 0.9.49 — Explicit Local Start Over

- Card-initiated local Jellyfin Start Over now adds an addon-owned
  `start_over=1` instruction to the existing opaque `play_jellyfin` route.
- `play_jellyfin` preserves the saved canonical resume state but omits that
  resume point from the resolved ListItem and supplies `StartOffset=0` for this
  explicit action.
- Confirmed card Resume behavior is unchanged and continues to use the saved
  Apollo/Jellyfin position without a Kodi resume dialog.
- Remote playback routes and resume behavior are unchanged.
