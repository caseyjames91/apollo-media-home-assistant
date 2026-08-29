# Apollo Media 0.9.84

- Fix AMS Continue Watching artwork disappearing after hydration: `blob:` artwork URLs are now accepted by the card renderer.
- Keep AMS artwork authoritative for AMS Continue Watching items instead of replacing it with legacy Home Assistant library artwork.
- Avoid replacing the Continue Watching rail when an AMS poll returns identical content, preventing unnecessary cross-card visual flashes.
- Add distribution scaffolding for Git-backed Kodi repository and HACS-managed Apollo card updates.
- Kodi playback/resume/source-selection behavior is unchanged from 0.9.83; only the add-on package version is bumped for repository distribution.
