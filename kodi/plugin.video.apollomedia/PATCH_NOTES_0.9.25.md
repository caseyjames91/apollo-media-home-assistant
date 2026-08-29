# Apollo Media 0.9.25

- `Play from Stream` now prompts when the local item has resume progress:
  - `Resume from H:MM:SS`
  - `Start from beginning`
- Resume uses the existing canonical Apollo/Jellyfin position.
- Choosing Start from beginning:
  - clears Apollo's canonical resume row for that identity;
  - clears any matching source-session resume;
  - resets Jellyfin's resume position to zero immediately;
  - starts the selected best remote stream from zero.
- Ongoing remote playback continues updating Jellyfin/Apollo normally.
- `Choose Remote Stream` remains the manual source-list path.
- Normal local playback behavior is unchanged.
