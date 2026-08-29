# Apollo Media 0.9.8

- Removes the unrequested MediaFusion provider added in 0.9.7.
- Adds Debridio as the third remote source provider.
- Keeps independent provider toggles:
  - Comet
  - Torrentio
  - Debridio
- Debridio accepts either:
  - a full Stremio web install URL containing `?addon=...`
  - a configured Debridio `manifest.json` URL
  - the configured Debridio addon root
- Apollo extracts the configured Debridio endpoint at runtime.
- No private Debridio/TorBox configuration URL is embedded in the addon package.
- Enabled providers are still queried concurrently, merged, deduplicated and
  passed through Apollo's common compatibility/ranking layer.
- No Jellyfin, playback-session, Home Assistant or metadata-authority changes.
