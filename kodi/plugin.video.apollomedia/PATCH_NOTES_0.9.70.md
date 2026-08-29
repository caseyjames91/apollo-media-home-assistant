# Apollo Media 0.9.70 — Canonical Episode Detail Playback

## Root cause: inconsistent episode detail actions
- Local episodes reached through different navigation paths were not carrying the same playback metadata.
- Direct/headless Jellyfin episode rows included remote targets, but `show_episodes()` rows did not.
- As a result, the same local episode could show `Play Locally` / `Choose Stream` from one entry point and only generic `Play` from another.
- This violated the global-detail-model contract: entry point was changing playback capabilities.

## Root cause: Kodi crash from card Play
- Some local episode rows exposed `play_jellyfin_native` as their directory file.
- That route intentionally calls Kodi `PlayMedia(...)` for Kodi-GUI-native behavior.
- The card then wrapped that GUI-native route inside Home Assistant `Player.Open`.
- Kodi could therefore enter nested/concurrent busy dialogs; the supplied log ends with:
  `Logic error due to two concurrent busydialogs, this is a known issue. The application will exit.`

## Fix: card-safe playback target
- Added an addon-owned `card_play_target` to canonical card route metadata.
- Kodi directory items can keep their GUI-native `play_jellyfin_native` target.
- The card now plays `card_play_target` instead of blindly reusing the directory item's GUI route.
- The card still receives only opaque Apollo plugin routes; it does not construct Jellyfin URLs.

## Fix: global local-episode capabilities
- `show_episodes()` now emits:
  - Jellyfin item identity
  - `in_library=1`
  - remote auto target
  - remote stream-picker target
  - card-safe local playback target
- Discovery-local episodes now emit the same card-safe local target.
- The detail renderer therefore sees the same local/remote capabilities regardless of whether the episode was reached from Continue Watching, Library, Show -> Season, or another canonical browse path.

## Preserved
- Remote-first card playback remains the default.
- Explicit `Play Locally` / `Resume Locally` remains available for library items.
- 0.9.68/0.9.69 source handoff/resume behavior is unchanged.
