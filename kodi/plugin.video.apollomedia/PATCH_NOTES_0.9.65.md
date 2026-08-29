# Apollo Media 0.9.65 — Dynamic Source Controls + Card Stream Picker

## One Now Playing card
- The same Now Playing UI is used for local Jellyfin and remote Apollo playback.
- Source-specific controls are rendered dynamically instead of using separate player UIs.
- Local playback shows `LOCAL · JELLYFIN`.
- Remote playback shows `REMOTE STREAM`, provider, and current stream position in the ranked session when available.

## Local -> remote handoff
- Local Now Playing can switch to remote playback without leaving the player.
- `Stream Remotely` uses Apollo's ranked remote resolver and preserves the current absolute playback position.
- `Choose Remote Stream` opens the same card stream picker and preserves the current position when a source is selected.

## Stream picker
- Added a headless addon route: `remote_stream_list`.
- The addon owns provider lookup, compatibility filtering, ranking, session state, flags, and opaque playback routes.
- Home Assistant only transports the addon-owned list to `sensor.apollo_streams`.
- The card never receives or constructs raw provider stream URLs.
- Clean streams stay first; flagged streams remain visible at the bottom, matching the Kodi chooser behavior.
- The currently selected source is identified in the picker.
- Selecting a different source during playback preserves the live playback position.

## Remote Now Playing controls
- Stream Picker
- Next Stream
- Flag Stream
- Flag Stream exposes the existing reasons:
  - Bad colors / HDR
  - No audio
  - Unsupported codec
  - Buffering
  - Wrong content
  - Wrong language
- Flagging keeps the existing Apollo behavior: flag the current source, learn from the flag, then advance to the next clean stream.

## Detail-page playback
- Local playable items expose `Stream Remotely`.
- Playable items with an IMDb identity expose `Choose Stream`.
- Existing normal Play behavior remains unchanged: local items still prefer Jellyfin.

## State ownership
- Addon remains authoritative for local/remote identity, source ranking, source session, flags, and playback resolution.
- Home Assistant remains transport/control plumbing.
- The card only renders the canonical active-source state and sends opaque Apollo plugin routes.

## Preserved
- 0.9.63 playback/resume foundation remains unchanged.
- 0.9.64 persistent refresh feedback remains unchanged.
