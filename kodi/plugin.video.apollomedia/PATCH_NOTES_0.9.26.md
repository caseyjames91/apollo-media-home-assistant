# Apollo Media 0.9.26

- Fixes the addon error when selecting `Play from Stream`.
- Root cause: the resume prompt used `xbmcgui.Dialog().context(...)`.
- Kodi's supported API is `xbmcgui.Dialog().contextmenu(...)`.
- No playback, progress, provider, ranking, or resume-authority logic changed.
