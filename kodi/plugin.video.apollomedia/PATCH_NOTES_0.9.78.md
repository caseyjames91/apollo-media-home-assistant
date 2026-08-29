# Apollo Media 0.9.78 — Mini Player Progress + Refresh Rail Inset Fix

## Minimized Now Playing
- Added a 3 px progress bar along the bottom edge of the minimized Now Playing card.
- It uses the same live playback position/duration calculation as the full Now Playing view.
- It updates through the existing one-second Now Playing ticker.
- Paused playback holds the current position; active playback continues to advance.

## Poster rail refresh stability
- Fixed poster rails occasionally appearing flush against the left edge after a media refresh.
- Tiny horizontal scroll offsets near the start of a rail are now normalized back to zero.
- Real user scroll positions farther into a rail are still preserved across refresh/rerender.
- Added explicit rail scroll padding and disabled browser scroll anchoring to protect the 17 px leading inset.

## Cache busting
- Card release stamp updated to `0.9.78`.
- Update the Lovelace resource suffix to `?v=0.9.78`.

## Scope
- Card UI/state preservation only.
- No playback resolver, source switching, provider, progress sync, or Home Assistant script behavior changed.
