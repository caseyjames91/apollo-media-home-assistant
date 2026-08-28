# Apollo Media Server

Apollo Media Server centralizes Apollo profile, catalog, progress, and device state.

## 0.1.7
- Runtime/UI/API/Jellyfin client version now inherit the Home Assistant build version.

## 0.1.6

The Web UI includes **Browse Apollo cache**, with Movies, Shows, and Continue Watching views. Artwork is proxied by Apollo so the Jellyfin access token is never placed in browser image URLs.

Database/API timestamps remain UTC. User-facing Web UI timestamps are rendered in the browser/device local timezone.

## Jellyfin

Connect Jellyfin from the add-on Web UI, then use **Sync library & Continue Watching**. Apollo caches Movies/Shows and profile resume state in SQLite and preserves last-known-good data when a remote sync fails.
