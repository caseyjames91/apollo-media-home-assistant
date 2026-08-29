# Apollo Media 0.9.47 — Card Local Playback Invocation

- Headless local Jellyfin entries now expose an opaque Apollo
  `play_jellyfin_native` route.
- That route launches the existing `play_jellyfin` route through Kodi's
  `PlayMedia(...)` built-in, matching Kodi's normal playable-item decision path
  so its configured native resume chooser can run.
- Headless local show navigation carries an addon-owned `native_local` marker
  through seasons and episodes so card-launched local episodes use the same
  wrapper without exposing or rewriting a media URL.
- Normal addon-directory local playback remains direct, and remote stream
  resume selection and offsets are unchanged.
