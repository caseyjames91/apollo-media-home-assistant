# Apollo Media 0.9.19

- Hotfix for Continue Watching runtime error introduced in 0.9.18.
- `add_jellyfin_movie()` now defines the movie IMDb id before calling the
  unified progress resolver.
- Removes the redundant later IMDb assignment.
- No changes to unified progress behavior, playback routing, source ranking,
  provider logic, or Jellyfin synchronization.
