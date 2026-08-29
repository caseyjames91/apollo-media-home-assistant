# Apollo Media 0.9.63 — Native Initial Resume + Shared Player UX

## Initial Resume / Start Over
- PlaybackSession remains the single authority that decides the canonical absolute position.
- Resolved local and remote ListItems expose that canonical position as Kodi resume metadata.
- Card playback passes its explicit Resume / Start Over choice to Kodi Player.Open `options.resume`.
- PlaybackMonitor no longer re-seeks after AVStart for initial `resume`, `start_over`, or `native` playback.
- This removes the visible 0:00 -> saved-position jump without restoring the 0.9.61 double-application bug.
- Post-AVStart absolute seek remains only for `live` source handoffs such as Try Next and playback-error failover.

## Kodi Addon Resume
- The resolved remote Kodi path no longer opens Apollo's second Resume / Start from beginning dialog.
- Kodi's native resume dialog is the only dialog when playback was initiated from Kodi.
- Legacy/native local and remote playback now also establish PlaybackSession state.

## Scrubber
- While dragging, displayed position and remaining time follow the temporary scrub position.
- The one-second player ticker cannot overwrite that temporary presentation state.
- Kodi receives the actual media_seek only when the scrubber is released.

## Play / Pause
- The card hydrates its current Kodi entity state before controls are used.
- One click maps explicitly:
  - playing -> media_pause
  - paused -> media_play
- Full Now Playing and mini-player share the same control path.

## Preserved
- 0.9.61 final Stop checkpoint and one-second internal position observation.
- Jellyfin progress/watched synchronization.
- Apollo progress ledger.
- Unified local/remote `play_resolved` contract.
- source_session / Try Next.
- Continue Watching semantics.
- Library paging foundation.
