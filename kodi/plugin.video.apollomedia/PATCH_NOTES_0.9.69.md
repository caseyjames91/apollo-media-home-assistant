# Apollo Media 0.9.69 — Now Playing Source Classifier Fix

## Root cause
- Remote -> local playback itself was completing correctly.
- The card still had the original card-started `_apolloPlayback.path` from the remote start.
- `isApolloRemotePlaybackActive()` treated that original `play_external*` path as enough to keep playback classified as remote.
- Because the media identity/title did not change, the remote controls could remain visible even after Kodi was playing the local Jellyfin stream.

## Fix
- During a requested source transition, `_expectedPlaybackSource` is now authoritative until a fresh Apollo Active Playback context confirms the new source.
- Expected `local` immediately classifies Now Playing as local.
- Expected `remote` immediately classifies Now Playing as remote.
- The original card-started playback route is now only a fallback before canonical active-source state exists.
- Source invalidation clears the cached Now Playing structural identity so same-title handoffs rebuild the controls.
- Local/remote switch completion also proactively rebuilds the open Now Playing modal while HA catches up.

## Scope
- No playback/resume behavior changed.
- 0.9.68 native remote->local resume remains intact.
- No provider/session ranking behavior changed.
