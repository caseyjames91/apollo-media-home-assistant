# Apollo Media 0.8.8

- Local Jellyfin shows now use Apollo/Cinemeta canonical display metadata when an IMDb id is available.
- Jellyfin remains authoritative for local availability, playback, resume, watched state and local artwork.
- Clearly broken Jellyfin show names such as `tvshows` fall back to the actual library folder name if canonical metadata is unavailable.
- Local show navigation keeps the canonical IMDb id so seasons/episodes can use canonical episode metadata.
- Preserve Continue Watching dedupe and artwork hierarchy.
- No Home Assistant/card changes.
