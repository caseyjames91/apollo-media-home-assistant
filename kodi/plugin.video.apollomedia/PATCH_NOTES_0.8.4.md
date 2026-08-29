# Apollo Media 0.8.4

- Fix numeric-only media titles at both Kodi list-label and VideoInfoTag title levels.
- Preserve a show's IMDb identity when entering seasons/episodes from the local Jellyfin library.
- Sanitize filename-like/generic local episode names instead of displaying raw Jellyfin names.
- Strip show prefixes, SxxEyy tokens, common release/source tags and file extensions.
- Fall back to canonical episode metadata, then Episode N when no useful title exists.
- Continue Watching episodes still force parent-series artwork.
- Preserve 0.8.1 dedupe and 0.8.2 artwork hierarchy.
- No Home Assistant/card changes.
