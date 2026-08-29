# Apollo Media 0.9.72 — Episode Row Progress + Source Badge Cleanup

## Episode rows
- Episode cells now use the episode name as the primary title.
- The show title is no longer repeated inside each episode cell.
- The second line is now the compact season/episode code (`S1 E1`, etc.).
- Episode progress moved off the thumbnail.
- In-progress episodes show a compact progress line inline with the season/episode code.
- Watched episodes render that line complete.
- Episode thumbnails still retain normal watched/library badges, but no longer carry the progress bar overlay.

## Now Playing source badge
- Normal remote playback no longer shows a source badge.
- Local playback continues to show the small `LOCAL` badge.
- Stream/provider/video/audio information is otherwise unchanged for now; the larger playback-info submenu cleanup remains a later UX pass.

## Scope
- No playback, source switching, resume, provider ranking, or Home Assistant logic changed.
- 0.9.71 canonical active/CW identity behavior is unchanged.
