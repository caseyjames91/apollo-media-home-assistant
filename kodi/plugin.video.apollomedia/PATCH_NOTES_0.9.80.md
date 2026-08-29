# Apollo Media 0.9.81 — Kiosk Viewport Fix

## Fix
- Apollo now detects Home Assistant views opened with the `?kiosk` URL parameter.
- In kiosk mode, the app shell uses the full dynamic viewport height instead of retaining the normal 56px Home Assistant header offset.
- The bottom navigation therefore remains anchored to the physical bottom of the available viewport when the HA header is removed.
- Normal, non-kiosk views keep the existing 56px header offset.

## Scope
- Functional change: `apollo-media-card.js`
- Version-only changes: Kodi addon version metadata, Jellyfin client version, language catalog project version.
- Unchanged but included: Home Assistant prototype YAML and all Kodi addon behavior/settings.

## Cache busting
- Use `?v=0.9.81` on the Lovelace card resource URL.
