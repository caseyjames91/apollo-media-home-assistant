# Apollo Media 0.9.3

- Removes Jellyfin metadata repair workarounds introduced in 0.9.1/0.9.2.
- Local library presentation now trusts Jellyfin metadata directly.
- Removes folder-name cleanup and title/year repair logic.
- Removes local title/year discovery matching.
- Removes season pre-filtering based on inferred episode membership.
- Removes TVMaze/local filename repair for Jellyfin episode titles.
- Keeps the normalized 0.9 MediaItem / MediaService / Kodi renderer architecture.
- Keeps fast Library Shows loading with no remote metadata lookup per show.
- Keeps existing Jellyfin playback/resume/reporting, TorBox, Comet/Torrentio,
  source ranking, Apollo progress, Try Next Stream, Flag Current Stream,
  playback failover, compatibility settings and auto-detect.
- Home Assistant/card remains deferred.
