# Apollo Media 0.9.81 — Unique Jellyfin Device Identity

- Replaces the shared Jellyfin `DeviceId="apollo-kodi"` with a persistent UUID unique to each Kodi profile.
- Stores the generated ID in Apollo addon data as `jellyfin_device_id.txt`.
- Uses the same per-install ID for Jellyfin authorization and local stream URLs.
- Prevents multiple Apollo/Kodi installations from presenting themselves to Jellyfin as the same device.
