# Apollo Media 0.9.14

- Replaces the single `Find Remote Streams` override with two explicit actions:
  - `Play from Stream` — bypass Jellyfin and auto-play Apollo's best ranked remote stream.
  - `Choose Remote Stream` — bypass Jellyfin and open the manual source chooser.
- Normal click on local items remains Jellyfin-first.
- Reuses existing `play_external` and `choose_external` flows.
- No changes to provider ranking, compatibility scoring or resume behavior.
