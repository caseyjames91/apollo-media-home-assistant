# Apollo Media 0.9.76 — Global Display Settings + Poster Spacing

## Global display settings
- Poster Size and Text Size are now global card settings.
- One adjustment applies across Home, Media Home, Library Home, Movie Library, and Show Library.
- Existing per-view values are migrated once into the global setting.
- This establishes a simple global baseline; a future feature can add explicit per-view overrides.
- `Reset current page options` is now `Reset display settings`.

## Poster spacing
- Horizontal poster rail spacing increased from 11 px to 14 px.
- Library poster grid column spacing increased from 11 px to 14 px.
- Vertical grid spacing is unchanged.

## Cache busting
- Card release stamp updated to `0.9.76`.
- Update the Lovelace resource suffix to `?v=0.9.76`.

## Scope
- Card presentation/settings only.
- No playback, provider, source switching, progress, or Home Assistant script behavior changed.
