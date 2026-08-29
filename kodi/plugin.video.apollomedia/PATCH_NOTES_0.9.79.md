# Apollo Media 0.9.79 — Kodi Settings Text Fix

## Fix
- Restored visible text throughout the Kodi addon Settings screen.
- `resources/settings.xml` already referenced Kodi localization IDs, but the addon had no language catalog defining those IDs.
- Added the complete English (`en_GB`) `strings.po` catalog for every category, group, setting label, heading, and help string currently referenced by Settings.
- No settings IDs or stored values changed, so existing configuration remains compatible.

## Cache busting
- Card release stamp updated to `0.9.79`.
- If updating the card resource too, use `?v=0.9.79`.

## Scope
- Kodi addon settings presentation only.
- No playback, provider ranking, Jellyfin sync, Home Assistant behavior, or card layout changed.
