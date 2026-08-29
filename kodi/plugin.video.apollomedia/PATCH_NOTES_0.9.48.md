# Apollo Media 0.9.48 — Card-Owned Continue Watching Decisions

- Headless Continue Watching local items now expose the direct Apollo
  `play_jellyfin` route; the card supplies Kodi's explicit JSON-RPC resume
  choice, so Kodi does not open a second native chooser.
- Headless Apollo-only Continue Watching items now expose `play_external`
  directly. Apollo retains source ranking, source sessions, compatibility,
  progress, and stream resolution while the card supplies the explicit resume
  choice.
- Normal Kodi addon Continue Watching keeps its existing native local resume
  behavior and Apollo remote resume chooser.
- No source URL is exposed to Home Assistant or the card.
