# Apollo Media 0.9.7

- Replaces the single Source Provider selector with independent provider toggles.
- Comet and Torrentio are enabled independently and can be used together or alone.
- Adds MediaFusion as a third source provider.
- MediaFusion accepts a configured Stremio addon/manifest URL in Settings.
- Queries all enabled providers concurrently.
- Merges, deduplicates and applies one common compatibility/ranking pass.
- A failed provider no longer prevents results from the other enabled providers.
- Stores provider identity in the active source session for later diagnostics.
- No changes to Jellyfin local-library metadata authority or Home Assistant/card work.
