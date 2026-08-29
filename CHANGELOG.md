# Changelog

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
