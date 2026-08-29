# Apollo Media 0.9.59
- Local card playback now resolves Jellyfin once and plays the final HTTP stream directly, avoiding JSON-RPC Player.Open on plugin:// URLs and Kodi's concurrent-busydialog crash path.
- Resume/Start Over are applied to the final local ListItem.
- Remote stream playback is unchanged.
- Full Library Shows/Movies are lazy-rendered only when selected, 120 at a time, with Load More for large libraries.
- Library Home rows are unchanged.
- Headless CW removal and CW ordering are unchanged.
