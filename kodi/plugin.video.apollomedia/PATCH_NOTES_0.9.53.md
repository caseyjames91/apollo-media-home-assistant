# Apollo Media 0.9.53 — Show Row Episode Context

- Headless show rows now carry a safe latest-episode presentation hint: season, episode, and episode title.
- Local Jellyfin library show hints are built from one batched Jellyfin episode query, preserving fast Library Shows loading without a per-show network request.
- Popular/Trending show hints use cached Cinemeta series metadata with bounded parallel lookups and exclude known future episodes.
- Show rows remain show folders; the episode hint is presentation-only and does not change canonical show identity, navigation, playback, resume, or Try Next behavior.
- No provider URLs, stream URLs, session data, or tokens are exposed.
