# Apollo Media 0.9.55 — Canonical Feeds and Library Home

- Rebuilt card-facing media contracts around canonical movie/show/season/episode identity without changing internal playback `series` semantics.
- Media Home base rows are Continue Watching, Up Next, Trending Shows, Trending Movies, Popular Shows, and Popular Movies.
- Up Next remains intentionally empty until a reliable watched-history authority is available.
- Cinemeta has no true Trending catalog; Apollo no longer mislabels its IMDb-rating Featured catalog as Trending. Trending feeds are intentionally empty pending Trakt integration.
- Popular Movies/Shows continue to use Cinemeta `top` catalogs.
- Added Library Home feeds for Recently Released Episodes, Recently Added Shows, Recently Released Movies, and Recently Added Movies.
- Added canonical route metadata for media type, presentation context, library state, IDs, release/add dates, and safe show/season browse targets.
- Library Shows now carries `last_episode_added` from one batched episode query; no per-show Jellyfin request loop was introduced.
- Card Library now has Home / Shows / Movies tabs, canonical episode/show/movie detail routing, episode show/season links, global in-library indicators, and media-type-valid Library sort options.
- Home Assistant prototype adds the new feed sensors and refreshes the canonical feed set.
