# Apollo Media 0.9.62 — Single Absolute Start Authority

## Root cause
0.9.61 correctly introduced one canonical PlaybackSession, but the resolved
ListItem still carried Kodi's `StartOffset` while PlaybackMonitor also called
Kodi's absolute `seekTime(requested_start_position)` after AVStart.

The observed 5:11 resume becoming about 5:13 after two seconds of startup was
the visible sign of two start-position mechanisms acting on the same request.

## Correction
- Unified resolved playback no longer sets Kodi `StartOffset`.
- PlaybackSession -> PlaybackMonitor is now the sole start-position authority.
- `requested_start_position` remains an absolute number of seconds.
- PlaybackMonitor applies it with Kodi's absolute `seekTime(seconds)` after AVStart.
- The correction is source-independent and therefore applies equally to:
  - direct Jellyfin playback
  - remote/provider playback
  - Resume
  - Try Next live-position handoff
  - playback-error failover
- Start Over remains a canonical zero position and performs no seek.

## Unchanged
- final Stop checkpoint behavior from 0.9.61
- 1-second internal position observation
- 10-second external progress cadence
- Jellyfin progress/watched sync
- Apollo progress ledger
- source_session/Try Next
- Library paging foundation
