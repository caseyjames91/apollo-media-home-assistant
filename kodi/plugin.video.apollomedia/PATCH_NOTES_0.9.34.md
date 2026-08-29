# Apollo Media 0.9.34 — Safe Resolution Capability Handling

- Stops attempting to infer maximum playback resolution from Kodi display/GUI labels.
- Testing showed `System.ScreenWidth/Height`, `System.ScreenMode`, and
  `System.ScreenResolution` can all expose the scaled/current Kodi GUI surface
  instead of the physical display capability.
- Device detection now preserves the user's existing 2160p/1080p/720p/480p toggles.
- The summary reports `Resolution: manual`.
- Kodi GUI dimensions are shown only as diagnostics and never affect source ranking.
- HDR, video codec, and audio-format detection remain automatic for now.
