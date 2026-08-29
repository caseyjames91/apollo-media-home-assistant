# Apollo Media 0.9.74 — Text Size Control + Cache-Buster Version Stamp

## Text size
- Added `Change Text Size` to Display Options.
- Opens the same small floating popup pattern as Poster Size so the card remains visible while adjusting.
- Range: 80%–130%; default: 100%.
- Existing typography hierarchy scales together.
- Saved separately for Home, Media Home, Library Home, Movie Library, and Show Library.
- Reset Current Page Options restores text to 100% and posters to 118 px.

## Cache busting
- Card carries `APOLLO_CARD_VERSION = "0.9.74"`.
- Append `?v=0.9.74` to the existing Home Assistant Lovelace resource URL for `apollo-media-card.js`.
- On future releases, only the `v=` value needs to change to force Fully Kiosk/other browsers to fetch the new card JS.

## Scope
- Card UI only.
- No playback, source switching, provider, resume, or HA script behavior changed.
