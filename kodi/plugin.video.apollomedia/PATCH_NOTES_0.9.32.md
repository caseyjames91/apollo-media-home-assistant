# Apollo Media 0.9.32 — Stream Chooser UX Redesign

- Removes the bottom Play / Flag / Close button row.
- Stream chooser now behaves like a normal Kodi list:
  - Up/Down: select stream
  - OK/Enter: play selected stream
  - C / Context Menu: Play + Flag Stream / Unflag Stream
  - Back: close
- Adds a small on-screen interaction hint.
- Reworks layout to a cleaner centered dark panel with a clear focused row.
- Flag icon is now a hardcoded bundled PNG texture in the row XML and is
  shown/hidden using structured `Apollo.Flagged` state.
- No Unicode/emoji icon dependency.
- Provider and flag reason remain visible as secondary row metadata.
- Ranking, playback, resume, Jellyfin synchronization and flag storage are unchanged.
