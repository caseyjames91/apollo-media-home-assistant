# Apollo Media 0.9.60 — Foundation Correction

## Playback
- Card-facing Jellyfin and remote playback now share `play_resolved`.
- Source-specific code ends at resolution; both sources produce the same final Kodi ListItem and use one setResolvedUrl player path.
- Home Assistant no longer parses Apollo URLs, item IDs, titles, or source type. It issues one Player.Open command.
- Jellyfin is accessed only through Apollo's own Jellyfin API client. No Jellyfin Kodi addon is required.
- PlaybackMonitor, Jellyfin progress sync, source sessions and Try Next remain intact.

## Library
- Full-library requests are bounded to 60-item pages rather than attempting to push the entire library through one HA sensor event.
- Jellyfin queries now support StartIndex; the collection contract accepts offset, limit, sort_by and sort_order.
- Library Home's small bounded rows are unchanged.
- This release establishes the paging contract. The card currently consumes the first page; interactive subsequent-page/sort controls are the next UI layer, not another transport redesign.

## Cleanup boundary
Legacy playback actions remain temporarily for direct navigation inside Kodi, but the Home Assistant card no longer uses them as its player contract.
