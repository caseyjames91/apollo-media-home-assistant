# Apollo Media 0.9.12

- Adds `Remove from Continue Watching` to the context menu for Continue Watching rows.
- Apollo remote-progress items remove their Apollo progress record.
- Jellyfin resume items clear only the Jellyfin resume position.
- When a canonical IMDb identity is available, Apollo also clears matching
  Apollo progress so a duplicate cannot immediately reappear.
- Normal library/discovery rows are unchanged.
- No provider ranking or playback-selection behavior changed.
