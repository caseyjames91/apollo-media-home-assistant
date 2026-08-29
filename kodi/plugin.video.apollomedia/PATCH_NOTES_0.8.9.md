# Apollo Media 0.8.9

- Restore fast My Jellyfin Shows loading by avoiding a canonical web lookup for every normal show.
- Repair only obviously broken Jellyfin show titles such as `tvshows`.
- Sort local shows by Apollo's repaired display title instead of Jellyfin's broken SortName.
- Add Kodi title sorting for the local show directory.
- Add cached TVMaze episode-title fallback when Cinemeta returns a generic show-name episode title.
- TVMaze lookup uses the exact IMDb series id and requires no API key.
- Preserve Jellyfin playback/resume/local-state behavior and existing artwork/Continue Watching fixes.
