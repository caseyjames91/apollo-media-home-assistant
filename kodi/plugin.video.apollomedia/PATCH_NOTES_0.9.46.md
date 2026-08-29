# Apollo Media 0.9.46 — Local Native Resume Prompt

- Local Jellyfin playback continues attaching canonical resume metadata but no
  longer forces Kodi's `StartOffset`, preserving Kodi's native Resume / Start
  from beginning prompt.
- Remote and selected-stream playback retain Apollo's explicit resume behavior.
- The Home Assistant card now skips overlapping periodic Continue Watching
  polls while preserving queued stop/config reconciliation.
