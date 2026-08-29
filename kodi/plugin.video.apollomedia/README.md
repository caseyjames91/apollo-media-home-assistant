# Apollo Media 0.7.1

Apollo Media is a thin Kodi-native, local-first movie and TV browser.

## Current foundation

- Popular and movie search discovery use canonical IMDb IDs.
- A cached Jellyfin index matches discovery titles to local movies.
- Jellyfin copies are labeled `IN LIBRARY` and are always preferred for playback.
- Jellyfin authentication uses a real user session so progress, resume, and watched state belong to the correct user.
- Continue Watching comes directly from Jellyfin.
- Kodi list items include native metadata, artwork, and resume points for skin compatibility.
- A lightweight background service reports playback start, progress, pause, seek, and stop to Jellyfin.
- Local TV discovery, search, series, season, and episode navigation use the same local-first matching and playback path.
- Discovery shows every known season and episode; individual episodes are labeled `IN LIBRARY` when Jellyfin has the matching season/episode number.
- Upcoming movies, shows, and episodes display their release date when available, with `UPCOMING` as a fallback. Release state never blocks an available source.
- Jellyfin availability uses the `IN LIBRARY` badge.
- Movies and episodes outside Jellyfin fall back to TorBox-cached Comet and Torrentio streams after a one-time TorBox device-code link.
- Provider results are queried concurrently, deduplicated, and ranked by resolution, source type, HDR/Dolby Vision, and lossless audio.
- Source lookup is silent. Device settings can limit preferred resolution, avoid Dolby Vision/HDR, or avoid AV1/HEVC; a context-menu **Choose remote source** action remains available for manual override.
- **Detect Device Compatibility** creates a per-Kodi profile from the active resolution, platform, reported HDR types, and audio passthrough configuration. Every resolution, HDR type, video codec, and audio format remains individually editable.
- Remote TorBox playback progress is stored locally by canonical IMDb/season/episode identity and merged into Apollo's Continue Watching alongside Jellyfin progress.
- Remote Continue Watching entries are enriched from Cinemeta with poster, fanart, plot, year, show title, and episode metadata.
- The ranked source list is retained during playback, allowing **Try Next Stream** without another search while carrying the current position forward.
- **Flag Current Stream** records HDR/color, audio, codec, buffering, or wrong-content problems and can update the device profile before trying the next result.
- Kodi playback errors automatically advance to the next ranked source. Headless actions are available for the planned Home Assistant remote, including an explicit **Show on TV** action.

## Setup

1. Open Apollo Media settings and enter the Jellyfin server URL.
2. Return to Apollo and select **Connect Jellyfin User**.
3. Enter the Jellyfin username and password. Apollo stores the returned access token and user ID; it does not store the password.
4. Select **Link TorBox**, approve the displayed device code, and choose Comet + Torrentio or either provider in Settings.

## Deliberately deferred

- TMDB and Trakt catalogs/state
- Merging local and remote entries in Continue Watching

The internal boundaries are designed for those additions without changing the validated Jellyfin playback path.

## Apollo Media Server
0.9.83 can use AMS as the profile-scoped Continue Watching authority. Configure the AMS URL under Apollo Media Server settings (default `http://homeassistant.local:8099`). If AMS has one profile, profile name/ID can remain blank.
