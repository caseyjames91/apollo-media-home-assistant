# Apollo Media 0.9.57 — Library Movies + Headless CW Removal

- Library Movies re-reads the authoritative HA sensor when the tab opens.
- Card-driven Remove from Continue Watching is explicitly headless.
- Headless removal no longer calls Kodi Container.Refresh or navigates Kodi's GUI.
- Kodi-native Remove from Continue Watching retains its existing refresh behavior.
- Successful card removal disappears optimistically, then reconciles with the authoritative CW feed.
- Episode detail gives Show title more prominence with Season directly beneath it.
- Continue Watching ordering logic is unchanged.
