# Apollo Media 0.9.0

- Introduces normalized media models (`MediaItem`, IDs, artwork, resume state).
- Adds `MediaService` as the browse/catalog normalization layer.
- Adds a dedicated Kodi renderer for normalized media items.
- Keeps existing Jellyfin playback/reporting, TorBox, Comet/Torrentio,
  source ranking, Apollo progress, Try Next Stream, Flag Current Stream,
  playback failover, compatibility settings, and auto-detect code intact.
- Standardizes the addon root around Continue Watching, Trending, Popular,
  Library, Search, device actions, and Settings.
- Home Assistant/card work remains intentionally deferred.
- Adds `TODO_VALIDATION.md` for one-by-one regression validation.
