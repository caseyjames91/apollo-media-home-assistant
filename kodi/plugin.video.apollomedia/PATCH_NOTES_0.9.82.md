# Apollo Media 0.9.82

- Moves the card's Continue Watching authority to profile-scoped Apollo Media Server (AMS) data when AMS is available.
- Uses Home Assistant's authenticated Supervisor ingress session and add-on discovery flow; no direct AMS port, token, or raw Jellyfin/provider URL is exposed to the card.
- Automatically discovers the installed Apollo Media Server add-on and its ingress URL. Optional `ams_addon_slug`, `ams_profile`, and `ams_profile_id` card settings are supported for explicit selection.
- Preserves the existing per-card `player_entity` playback target and all validated local/remote playback routes.
- Keeps the legacy Home Assistant Continue Watching sensor as a safe fallback if AMS is unavailable during this migration stage.
- Continue Watching refresh now asks AMS to sync Jellyfin before reloading the profile-scoped rail.
- This first AMS migration covers Jellyfin-backed profile progress. Remote-only Apollo progress remains on the existing addon path until Kodi-to-AMS progress reporting is implemented.
