# Apollo Media 0.9.41 — Global Continue Watching Order

- Merges Jellyfin resume items and Apollo-only progress entries into one intermediate timeline before rendering.
- Sorts the merged timeline newest-first using Jellyfin `UserData.LastPlayedDate` and Apollo `progress.updated`.
- Keeps timestamp-less entries after timestamped entries.
- Preserves canonical IMDb + season + episode dedupe, including the existing Jellyfin identity fallbacks.
- When both stores contain the same identity, the existing Jellyfin-first canonical progress behavior remains unchanged.
- Applies the same ordering to Kodi and headless/Home Assistant Continue Watching routes.

No playback routes, progress identity, completion behavior, removal behavior, providers, ranking, compatibility, or UI styling changed.
