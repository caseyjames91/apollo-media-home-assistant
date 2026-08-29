# Apollo Media 0.9.13

- Adds `Find Remote Streams` as a manual playback override for local Jellyfin items.
- Normal click behavior remains local-first via Jellyfin.
- Local movies with canonical IMDb identity can open the existing remote-source chooser.
- Local episodes with canonical show IMDb + season + episode identity can open the existing remote-source chooser.
- Discovery episodes that are local use the `Find Remote Streams` label for the existing chooser action.
- Reuses the existing Comet / Torrentio / Debridio source pipeline; no duplicate provider logic added.
- No changes to default playback priority, source ranking, resume behavior, or Jellyfin metadata authority.
