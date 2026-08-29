# Apollo Media 0.9.1

- Fix Library Shows performance by removing per-show remote metadata lookups.
- Repair clearly broken Jellyfin show titles from the Jellyfin folder name without network calls.
- Sort Library Shows by Apollo's repaired display title.
- Route local show seasons and episodes through the normalized MediaService layer.
- Resolve canonical show metadata only after a show is opened.
- Use canonical episode title/plot when available while preserving Jellyfin
  local identity, playback, resume and artwork.
- Home Assistant/card remains out of scope.
