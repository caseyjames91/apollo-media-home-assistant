# Apollo Media 0.9.27

- Adds `Choose Remote Stream` to non-local discovery movies.
- Adds `Choose Remote Stream` to non-local discovery episodes where the
  normalized episode renderer is used.
- Normal click behavior is unchanged:
  - local item -> Jellyfin
  - non-local item -> automatically chosen best-ranked remote stream
- Local items still additionally expose `Play from Stream`.
- No provider, ranking, resume, or playback-monitor logic changed.
