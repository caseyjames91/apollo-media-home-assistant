# Changelog

## 0.2.3
- Mount Home Assistant's `/ssl` directory read-only into the Apollo Media Server add-on.
- Install `/ssl/Apollo+CA.crt` into the add-on container trust store at startup when present.
- Keep normal TLS certificate verification enabled for internal HTTPS services such as Radarr and Sonarr.
- Add the Alpine `ca-certificates` package explicitly so custom CA trust installation is deterministic.
- Log whether the custom Apollo CA was installed or the system trust store is being used.


## 0.2.2
- Make Radarr the local-availability authority for movies and Sonarr the local-availability authority for shows and episodes.
- Add saved Radarr/Sonarr integration configuration and connection-test API endpoints without exposing stored API keys in reads.
- Add `/local-availability/sync` to reconcile Apollo media against Arr libraries, including marking previously-known items unavailable when files disappear.
- Match Radarr movies by TMDB/IMDb identity and Sonarr series by TVDB/IMDb identity, then resolve Sonarr episodes by season/episode number.
- Decouple `available_locally` from Kodi path translation. Arr can now truthfully mark an item local even while Apollo's final Kodi local-playback transport is still unset.
- Preserve legacy path-mapping/manual-local endpoints for development compatibility; no fake SMB mapping is required for Arr-backed availability.

## 0.2.1
- Add an idempotent SQLite startup migration so databases created by AMS 0.1.x are upgraded in place for the Apollo-owned 0.2 schema instead of failing on missing ORM columns.
- Migrate legacy profile fields required by 0.2 (`profile_type`, `avatar`, `pin_required`, `created_at`) and backfill existing profile timestamps.
- Migrate 0.2 media metadata fields (`tvdb_id`, `series_title`, `year`, `overview`, `poster_url`, `backdrop_url`) and provider-ID indexes.
- Migrate progress watched-state fields (`watched`, `watched_at`) and the integration `name` field while preserving legacy columns and existing data.
- Align the development/default database URL with the add-on runtime database at `/config/apollo.db`.

## 0.1.8
- Fix AMS runtime version resolving to `dev` inside the container.
- Re-declare Home Assistant `BUILD_VERSION` inside the Docker build stage before exporting `APOLLO_VERSION`.
- Keeps the Web UI, API, health endpoint, logs, and Jellyfin client version aligned with the add-on package version.

## 0.1.7
- Runtime version now comes from Home Assistant `BUILD_VERSION`, sourced from `config.yaml`.
- Removed stale hard-coded 0.1.5 runtime/UI/client version strings.
- Added release verification to prevent package/runtime version drift.

## 0.1.6
- Enrich profile-scoped Continue Watching responses with canonical provider IDs, Jellyfin item IDs, series identity, and artwork identity so Apollo clients can render and play cached items without relying on shared Home Assistant feed sensors.
- Keeps AMS as the profile-state authority while Kodi remains the playback target.

## 0.1.5
- Add Apollo Cache Browser for visually inspecting cached Movies, Shows, and profile Continue Watching.
- Show Jellyfin artwork through an authenticated Apollo image proxy; access tokens are not exposed to the browser.
- Show canonical, IMDb, TMDB, Jellyfin IDs, episode numbers, progress, and update times in the browser.
- Display user-facing timestamps in the browser/device local timezone while retaining UTC storage internally.
- Add `release-update.sh` to validate, unpack, stage, commit, and push future release ZIPs with one command.
- Bump API/Jellyfin client/server version reporting to 0.1.5.

## 0.1.4
- Add Jellyfin catalog import/cache and profile-scoped Continue Watching sync.
- Add last-known-good cache protection when Jellyfin fetches fail.
- Add catalog and sync APIs plus UI sync/status controls.

## 0.1.3
- Preserve Home Assistant ingress base paths for setup form actions, redirects, and links.

## 0.1.2
- Add Jellyfin connection setup, token persistence, connection testing, disconnect, and profile mapping.

## 0.1.9
- AMS Continue Watching is now the canonical merged profile timeline for Jellyfin and Kodi-reported remote progress.
- Added timestamp-preserving batch progress import so multiple Kodi clients can merge historical progress without stale devices winning.
- Jellyfin sync no longer overwrites newer AMS progress.
- Exposes the AMS API on port 8099 for Kodi clients; Home Assistant ingress remains the browser/card path.
