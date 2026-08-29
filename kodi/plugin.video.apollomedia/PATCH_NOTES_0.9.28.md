# Apollo Media 0.9.28

- Standardizes `Choose Remote Stream` as a universal context-menu action on
  playable movies and episodes with a known IMDb identity.
- Applies to:
  - local discovery movies
  - non-local discovery movies
  - local discovery episodes
  - non-local discovery episodes
  - normalized Popular / Trending / Search movie rows
  - local library movie/episode rows
  - Apollo remote Continue Watching entries
- Local items still additionally expose `Play from Stream`.
- Normal click behavior is unchanged:
  - local -> Jellyfin
  - remote -> best-ranked remote source
