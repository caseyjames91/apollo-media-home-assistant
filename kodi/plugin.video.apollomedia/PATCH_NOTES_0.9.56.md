# Apollo Media 0.9.56 — Global Detail Shell and Continue Actions

- Restores Library Movies resilience by refreshing its dedicated feed when the Movies tab opens empty.
- Standardizes Movie, Show, Season, and Episode details on one full-card shell above the persistent navigation/mini-player area.
- Season detail now uses parent-show identity plus season metadata instead of inheriting the first episode as its header.
- Season summaries are carried from Jellyfin when available.
- Continue Watching episode routes carry safe show/season navigation targets for both Jellyfin and Apollo-only progress items.
- Adds card-side Remove from Continue Watching through the existing addon `remove_continue` action and a dedicated safe HA script.
- Detail navigation now retains Back history for Show → Season → Episode and for episode breadcrumb navigation.
- Existing playback, Resume/Start Over, Try Next, progress authority, source ranking, and provider behavior are unchanged.
