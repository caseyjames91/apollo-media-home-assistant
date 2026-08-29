# Apollo Media 0.9.30 — Custom Stream Chooser Prototype

- Replaces Kodi's generic source-directory UI for `Choose Remote Stream`
  with an Apollo-owned `WindowXMLDialog`.
- Bundles a PNG flag badge, so flagged-state UI no longer depends on Unicode
  emoji/icon font support.
- Stream rows show:
  - stream title;
  - provider;
  - flag reason when present;
  - image badge for flagged streams.
- Flagged sources remain visible and sort below clean sources.
- Bottom buttons:
  - Play
  - Flag Stream / Unflag Stream
  - Close
- Existing flag reasons and stream-session data are reused.
- `Wrong language` remains available.
- Ranking, auto-play, resume, Jellyfin sync, Try Next Stream and active
  Flag Current Stream behavior are unchanged.
