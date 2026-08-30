# Apollo Media 0.9.87 — AMS Local Playback Pilot

- Adds an AMS device key setting for device-aware local path resolution.
- Adds strict IMDb + season/episode AMS media lookup without title matching.
- Normal local Kodi clicks now enter the existing unified playback resolver.
- When AMS knows the media, its playback-resolution decision is authoritative:
  - `mode=local` opens the device-mapped path (SMB/NFS/etc.) directly in Kodi.
  - `mode=remote` falls through to Apollo's existing remote-provider flow.
- Jellyfin remains a transitional metadata/resume adapter and a legacy playback fallback only when this Kodi is not opted into AMS routing or AMS does not yet know the identity.
- Existing remote source ranking, TorBox, Try Next, flagging, and compatibility logic are unchanged.
- Card/headless live local switching remains on its previous path for this pilot; migrate it only after direct Kodi local resolution is validated.
