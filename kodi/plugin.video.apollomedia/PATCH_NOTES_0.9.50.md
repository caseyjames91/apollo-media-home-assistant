# Apollo Media 0.9.50 — Explicit Remote Playback Intent

- Card-driven remote playback now carries `resume_mode=resume` or
  `resume_mode=start_over` into Apollo's `play_external` route.
- Resume resolves the canonical saved position once and stores that exact
  position and intent in `source_session` for later startup synchronization.
- Start Over creates a zero-position source session without reading or deleting
  historical progress; both the resolved item and playback service therefore
  avoid falling back to prior progress. `StartOffset=0` is authoritative and
  the service does not issue a redundant zero seek callback.
- Remote startup events no longer persist transient pre-seek positions.
- Try Next and playback-error source recovery update the active source session
  to the current live position before starting the replacement stream.
- Normal Kodi-side remote prompts and local Jellyfin playback are unchanged.
