# Changelog

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
