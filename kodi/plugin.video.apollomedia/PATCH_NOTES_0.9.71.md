# Apollo Media 0.9.71 — Canonical Active/CW Identity Fix

## Root cause: new/resumed items lost source controls
Two separate paths could produce the stripped-down Now Playing state:

1. Active Playback was validated by exact presentation title.
   Episode labels can legitimately differ between Kodi, Jellyfin, discovery
   metadata, and Apollo progress (for example `Episode 1` vs a real episode
   title). The addon had already verified the playing file, but the card then
   discarded that valid active context because the titles did not match.

2. Apollo-only Continue Watching rows did not recover their Jellyfin identity.
   If Apollo progress became visible before Jellyfin's resume list caught up,
   the CW row was treated as remote-only even when the episode existed locally.
   Resuming that row therefore lost `Play Locally`, Stream Picker, and the
   Jellyfin item ID needed for source switching.

## Fixes
- Active Playback is no longer gated by exact title equality.
- Season/episode numbers are used as an additional identity guard when Kodi
  exposes them.
- Added a canonical IMDb(+S/E) -> Jellyfin lookup.
- Apollo-progress CW entries now recover the matching Jellyfin item when it
  exists and carry the same:
  - `in_library`
  - Jellyfin item ID
  - remote auto target
  - remote picker target
  - local card-play target
  - remote resume_item_id
  as Jellyfin-originated CW entries.
- `show_episodes()` now backfills the series IMDb directly from Jellyfin when a
  navigation route omitted it, preventing nested local episodes from losing
  remote capabilities.

## Preserved
- Remote-first card playback.
- Native source handoff resume behavior.
- Global detail renderer and card-safe playback target.
