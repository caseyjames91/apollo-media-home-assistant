# Apollo Media 0.9.45 — Continue Watching Diagnostics

- Adds temporary structured `APOLLO_CW_DEBUG` logging to the shared Continue Watching timeline builder.
- Logs every candidate before sorting, the complete title order after sorting, and every final entry with its canonical identity and both activity sources.
- Labels normal Kodi loads as `GUI` and Home Assistant/headless loads as `HEADLESS`.
- Logs each consumer's exact `addDirectoryItem` dispatch order and confirms one timeline-builder call per route invocation.

This diagnostic build does not change Continue Watching sorting, playback,
progress synchronization, source selection, flags, resume prompts, or UI behavior.
