# Apollo Media 0.9.2

- Keep fast Library Shows behavior from 0.9.1.
- Normalize folder-derived show labels by removing trailing year/provider tags.
- Filter season containers using actual local Jellyfin episodes so empty
  seasons no longer open blank directories.
- Resolve a local show's canonical IMDb identity when the show is opened.
- Repair missing/wrong Jellyfin provider identity using discovery title/year matching.
- Forward the resolved IMDb identity from Seasons to Episodes.
- Strengthen local episode-title resolution with TVMaze and filename-title fallback.
- Preserve existing playback/source/device functionality.
