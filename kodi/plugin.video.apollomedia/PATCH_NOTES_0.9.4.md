# Apollo Media 0.9.4

- Replaces the large `IN LIBRARY` badge with a subtle gray dot (`•`).
- Applies the same local marker to movies, shows, seasons and episodes.
- Library Shows remains a direct Jellyfin library view.
- Popular/Trending/Search shows now remain in the unified discovery catalog
  even when the show exists locally.
- Discovery seasons are overlaid with Jellyfin membership by canonical show
  IMDb identity + season number.
- Discovery episodes continue to overlay Jellyfin membership by season +
  episode number.
- Local discovery episodes play through Jellyfin.
- Non-local discovery episodes use Apollo remote playback.
- No Jellyfin metadata repair logic is introduced.
