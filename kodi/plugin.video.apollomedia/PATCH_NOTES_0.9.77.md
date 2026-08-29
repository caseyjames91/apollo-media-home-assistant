# Apollo Media 0.9.77 — Global Padding / Card Spacing Control

## Display settings
- Added `Change Padding` beside Poster Size and Text Size.
- Uses the same compact floating popup so the card stays visible while tuning.
- Adjusts spacing between poster cards live.
- Range: 6–28 px.
- Default: 14 px, matching 0.9.76.
- Global across all media views.
- Library grid column spacing follows the same setting as horizontal poster rails.
- Stored as `apollo-media.card-spacing`.
- Reset Display Settings restores 14 px.

## Cache busting
- Card release stamp updated to `0.9.77`.
- Update the Lovelace resource suffix to `?v=0.9.77`.

## Scope
- Card display/settings only.
- No playback, progress, provider, source switching, or Home Assistant script behavior changed.
