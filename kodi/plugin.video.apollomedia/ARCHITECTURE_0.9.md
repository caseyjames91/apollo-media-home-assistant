# Apollo Media 0.9 Architecture

## Goal

Apollo 0.9 keeps the proven playback/source/device code from 0.8.x while
standardizing all browsing around one normalized media model.

## Layers

- `resources/lib/models.py`
  - Canonical `MediaItem`, IDs, artwork, and resume state.
- `resources/lib/media_service.py`
  - Normalizes Jellyfin and discovery data.
  - Applies local-library membership.
  - Keeps source-specific logic out of Kodi routes.
- `resources/lib/render/kodi.py`
  - Renders normalized media items into Kodi ListItems.
- Existing Jellyfin/source/progress/compatibility modules
  - Retained as adapters/services.
- `main.py`
  - Routes and orchestration only.

## Authority model

- Local library metadata / structure / membership / playback / resume: Jellyfin
- Remote resume: Apollo progress DB
- Discovery metadata: Apollo discovery layer
- Remote sources: Comet/Torrentio + TorBox
- Watched/history and discovery lists: Trakt planned
- Home Assistant Apollo Media Card: primary media frontend
- Kodi: playback/rendering endpoint and optional TV-side frontend
- Apollo Kodi addon: standalone optional Kodi UI plus shared Kodi-side functionality
- Home Assistant: room/activity orchestration

## Product interaction contract

- A user must be able to browse, select, configure, and control playback entirely
  from the Apollo Media Card without interacting with Kodi's UI.
- Browsing on the card must not change Kodi's UI or navigation context.
- Kodi UI/context changes only for an explicit `Send to TV` action, direct Kodi
  interaction, or what is inherently required to display playback.
- Decisions created by card actions belong on the card. This includes resume vs.
  start over and, as the card evolves, local vs. stream, source selection,
  flag/unflag/try-next, subtitles, and audio tracks.
- Card playback commands must be explicit and unambiguous so Kodi does not show
  a second decision dialog.
- `Send to TV` will transfer semantic browsing context to the Kodi addon; it will
  not mirror the Lovelace UI. Generalized context synchronization remains future
  work.
- Preserve configurable Kodi `player_entity`; no fixed player target is part of
  the architecture.

## Card state model

- Selected item, detail/modal state, and playback action are separate concepts.
- Selecting an item may open a reusable Apollo item-details surface without
  causing playback.
- Continue Watching is the first entry point for this details surface, not a
  special-purpose terminal design.
- Local Jellyfin/Kodi playback and remote Apollo playback retain their existing
  source-specific implementations beneath the common card interaction.

## Root menu

- Continue Watching
- Trending Movies
- Trending Shows
- Popular Movies
- Popular Shows
- Library Movies
- Library Shows
- Search Movies
- Search Shows
- TorBox / device / settings actions

## Important

0.9.0 is the first architecture build. Existing playback functions are
intentionally retained rather than rewritten so they can be validated
feature-by-feature.
