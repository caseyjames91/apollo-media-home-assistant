# Apollo Media 0.9.75 — Rail Alignment + Episode Subtitle Cleanup

## Rail alignment
- Poster rails now explicitly top-align their cards.
- Poster position no longer shifts when neighboring items have taller title/subtitle content.
- Existing two-line title reservation remains intact so subtitle rows stay aligned.

## Episode subtitle cleanup
- Fixed Continue Watching episode metadata such as:
  `S1 E1 · S1 E1 · Pilot`
- The rail formatter now recognizes both `S1E1` and `S1 E1` source formats before rebuilding the canonical display.
- Result is now:
  `S1 E1 · Pilot`

## Cache busting
- Card release stamp updated to `0.9.75`.
- If your Lovelace resource uses the cache-buster query string, update it to:
  `?v=0.9.75`

## Scope
- Card presentation only.
- No playback, progress, source switching, providers, or Home Assistant scripts changed.
