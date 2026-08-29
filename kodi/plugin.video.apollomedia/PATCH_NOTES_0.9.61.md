# Apollo Media 0.9.61 — Canonical Playback Lifecycle

This is a downstream playback-lifecycle correction shared by Jellyfin and remote playback.

## Canonical PlaybackSession
- Adds one safe `playback_session.json` contract created before Kodi starts playback.
- Stores source-independent media identity, requested start position, resume mode,
  tracking target, and current checkpoint.
- Stores no provider/stream URL.

## Resume
- PlaybackMonitor applies the canonical requested start position in one place after
  AVStart for both Jellyfin and remote/provider media.
- Resume is no longer dependent on source-specific ListItem bookmark behavior.
- Start Over remains zero and does not perform a second zero seek.
- Try Next and playback-error failover update the same PlaybackSession with a live
  requested start position; duplicated source-specific seek loops were removed.

## Progress lifecycle
- PlaybackMonitor continuously observes the live Kodi position once per second in memory/session state.
- External Apollo/Jellyfin progress writes remain on the existing 10-second cadence,
  plus pause, resume, seek, and stop.
- Seek captures the Kodi callback target immediately.
- Stop performs a mandatory final checkpoint using the latest observed position even
  if Kodi's getTime() is already unavailable by the time Stop fires.
- Jellyfin-backed remote playback and direct Jellyfin playback use the same tracking path.

## Preserved
- Unified 0.9.60 `play_resolved` source resolution contract.
- Jellyfin progress/watched reporting.
- Apollo progress ledger.
- source_session ranking/flags/Try Next.
- Continue Watching logic.
- Library paging foundation.
