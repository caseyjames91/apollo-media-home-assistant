# Apollo Media 0.9.39 — Remote Resume Presentation + Prompt

Remote-only progress is now treated consistently across Apollo:

- Popular / Trending / Search movie rows attach Apollo progress to the Kodi
  ListItem, so the native resume/progress indicator is visible.
- Remote discovery episode rows attach Apollo progress as well.
- Normal click on a remote movie/episode with progress now asks:
  - Resume from ...
  - Start from beginning
- Remote items without progress continue directly to playback with no needless prompt.
- Start from beginning clears the canonical Apollo progress identity before playback.
- Remote Continue Watching items use the same resume/beginning choice.
- Local Jellyfin playback and local Play from Stream behavior are unchanged.

Current Stream Info:
- provider and source number are moved into the dialog heading so Kodi skins
  cannot clip those lines from the body.
