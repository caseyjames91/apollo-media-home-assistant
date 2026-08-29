# Apollo Media 0.9.22 — Progress Reconciliation Fix

- Replaces timestamp-based Jellyfin reconciliation with last-synced-position
  change detection.
- Apollo stores the Jellyfin position it last synchronized for each canonical
  media identity.
- If Jellyfin later reports a different position, Apollo treats it as external
  Jellyfin-app playback and imports it.
- Local Kodi playback and local remote-stream playback update the Apollo ledger
  and the Jellyfin synchronization snapshot together.
- Local Jellyfin playback now explicitly supplies the canonical StartOffset.
- Remote playback now explicitly supplies StartOffset even when the canonical
  position is zero.
- This prevents old Kodi URL-specific bookmarks from taking precedence over
  the canonical media-identity progress.
