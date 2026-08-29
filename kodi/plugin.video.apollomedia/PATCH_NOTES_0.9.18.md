# Apollo Media 0.9.18 — Unified Progress

Progress is now identity-based rather than playback-URL-based.

Canonical identity:
`IMDb + season + episode`

Behavior:
- Apollo's progress database is the Kodi-side progress ledger.
- Local playback updates Apollo and Jellyfin.
- A local item played through a remote stream updates Apollo and Jellyfin.
- Remote-only media updates Apollo.
- Newer Jellyfin-app progress is imported into Apollo when the local item is
  next resolved.
- Newer Apollo progress is mirrored back to Jellyfin for local media.
- Legacy pre-0.9.18 local Apollo rows lose once to Jellyfin during migration,
  preventing stale remote URL resume values from overriding current Jellyfin
  progress.
- Remote stream playback explicitly seeks to the canonical identity resume
  point so Kodi's bookmark for an individual stream URL cannot become the
  authority.
