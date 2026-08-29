# Apollo Media 0.9.38 — Current Stream Info

Adds `Current Stream Info` whenever an Apollo remote source session is active.

The dialog reads Apollo's own `source_session` instead of Kodi playlist or
container metadata and shows:
- provider
- exact source title
- current source number / total source count
- flagged state
- flag reason when present

This is intended to be the authoritative way to identify which remote source
Apollo actually selected. Kodi's playlist may only show the movie/show title
or an internal filename and is not used for source validation.

No ranking, playback, resume, provider, compatibility, or flag behavior changed.
