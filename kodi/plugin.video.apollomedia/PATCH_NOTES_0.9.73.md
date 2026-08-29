# Apollo Media 0.9.73 — Poster Size Popup

## Display Options
- Replaced the inline poster-size slider with a `Change Poster Size` button.
- The button shows the current poster size for the active card context.
- Clicking it closes Display Options and opens a small floating poster-size popup.
- The underlying card remains visible while the slider is adjusted, making size changes much easier to judge.

## Behavior preserved
- Poster size still updates live while dragging.
- Size is still saved separately per supported context:
  - Home
  - Media Home
  - Library Home
  - Movie Library
  - Show Library
- Existing 90–150 px range is unchanged.
- Reset Current Page Options still restores the active context to 118 px.
- No playback, addon, provider, or Home Assistant behavior changed.
