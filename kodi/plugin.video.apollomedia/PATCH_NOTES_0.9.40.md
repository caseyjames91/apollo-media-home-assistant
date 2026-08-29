# Apollo Media 0.9.40 — Unify Trending Rendering

Fixes remote progress not appearing in Trending Movies.

Root cause:
- Popular Movies and Search Movies used the normalized `MediaService` +
  `render_movie_media()` path.
- Trending Movies still used the older `remote_media_list` /
  `remote_movie_catalog` / `add_discovery_movie` path.
- Progress identity was already the same IMDb identity, so playback resumed
  correctly, but the legacy Trending renderer did not attach resume metadata.

Changes:
- Kodi root Trending Movies now uses `MediaService.trending_movies()` and
  `render_movie_media()`.
- Kodi root Trending Shows now uses `MediaService.trending_shows()` and
  `render_show_media()` for the same architectural consistency.
- The older `add_discovery_movie()` path also now attaches canonical local or
  Apollo remote progress, so headless/remote consumers do not diverge.

No progress keys, playback behavior, ranking, providers, flags, or resume
authority changed.
