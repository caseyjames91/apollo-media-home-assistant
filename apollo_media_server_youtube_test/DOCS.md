# Apollo Media Server

Apollo Media Server centralizes Apollo profile, catalog, progress, and device state.

## 0.1.8
- Runtime/UI/API/Jellyfin client version now inherit the Home Assistant build version.

## 0.1.6

The Web UI includes **Browse Apollo cache**, with Movies, Shows, and Continue Watching views. Artwork is proxied by Apollo so the Jellyfin access token is never placed in browser image URLs.

Database/API timestamps remain UTC. User-facing Web UI timestamps are rendered in the browser/device local timezone.

## Jellyfin

Connect Jellyfin from the add-on Web UI, then use **Sync library & Continue Watching**. Apollo caches Movies/Shows and profile resume state in SQLite and preserves last-known-good data when a remote sync fails.

## Kodi clients (0.1.9+)
Kodi clients use the direct AMS API on port 8099 for profile progress and Continue Watching. The Kodi addon defaults to `http://homeassistant.local:8099`; change the AMS URL in Kodi settings when the Home Assistant host is reached by another hostname/IP.
