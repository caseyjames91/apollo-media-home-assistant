# Apollo Media 0.9.20

- Adds `Clear Progress` to local movie/episode context menus.
- Clear Progress removes:
  - Apollo's canonical identity progress row
  - Jellyfin resume position
  - matching source-session resume position
- `Remove from Continue Watching` now also clears matching source-session resume.
- The gray dot in discovery lists remains the intentional `in library` marker;
  it is not a progress marker.
- This build is intended to provide a deterministic zero-progress test state.
