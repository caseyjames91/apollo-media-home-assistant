# Apollo Media 0.9.44 — Stable Continue Watching Activity

- Prevents local Continue Watching rendering from assigning the current wall-clock time to Apollo progress activity.
- Jellyfin resume imports now preserve `UserData.LastPlayedDate` as their activity timestamp.
- When Jellyfin has no usable activity date, resume synchronization preserves an existing Apollo `progress.updated` value or uses a neutral zero timestamp.
- Normal and headless Continue Watching routes explicitly advertise Kodi's unsorted mode so Apollo's newest-first insertion order remains authoritative.

Playback reporting still records genuine new activity normally. Playback routes,
resume decisions, source ranking, chooser behavior, flags, and presentation are unchanged.
