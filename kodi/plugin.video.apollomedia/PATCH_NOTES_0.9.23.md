# Apollo Media 0.9.23

- Repairs local Kodi -> Jellyfin resume synchronization.
- Jellyfin playback-session events are still sent for activity/watched-state behavior.
- On progress and stop, Apollo now also writes the current resume position
  directly to Jellyfin user data via `set_resume()`.
- Local playback and local-item remote overrides both use the same explicit
  Jellyfin resume write.
- Apollo's identity progress ledger remains synchronized to that same position.
- No provider, source-ranking, metadata, or menu behavior changed.
