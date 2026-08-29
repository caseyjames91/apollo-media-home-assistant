# Apollo Media 0.9.31 — Custom Dialog Visual Fix

- Fixes the transparent/broken 0.9.30 custom stream chooser.
- Root cause: the XML relied on `white.png`, which is a skin asset and was not
  available through the addon-owned dialog.
- Bundles Apollo-owned textures for:
  - full-screen dialog background
  - dialog panel
  - focused stream row
  - normal button
  - focused button
- The dialog no longer depends on the active Kodi skin for those textures.
- Tightens the list/button spacing slightly.
- Stream chooser behavior, flags, ranking, resume and playback logic are unchanged.
