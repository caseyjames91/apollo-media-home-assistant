# Apollo Media Home Assistant

Home Assistant add-on repository for **Apollo Media Server**, the central catalog, profile, progress, and device-state service for Apollo Media.

Current release: **0.1.8**

Apollo stores application timestamps in UTC and renders user-facing server timestamps in the browser/device local timezone. The add-on currently uses SQLite in persistent Home Assistant add-on storage.

## Development releases

After uploading a future `Apollo-HA-Addon-X.Y.Z-update.zip` to the repository root, run:

```bash
./release-update.sh Apollo-HA-Addon-X.Y.Z-update.zip
```

The helper validates the tree/archive, applies the update, stages it, verifies the diff, commits the version, and pushes `main`.

### Kodi client connection
AMS 0.1.9 exposes its direct API on TCP 8099 so Kodi addons can report and consume profile state without routing through Home Assistant ingress. Browser/card clients continue to use authenticated HA ingress. Direct API authentication is a pre-public-release hardening item.

## Kodi repository

Apollo Media's Kodi add-on is published from `kodi-repository/`. Install `repository.apollomedia-1.0.0.zip` once on each Kodi device; future `plugin.video.apollomedia` versions are then available through Kodi's normal update system. The repository uses HTTPS GitHub-hosted metadata and SHA-256 package hashing.

## Apollo Media Card via HACS

The card source lives in `card/apollo-media-card.js` and the HACS distribution copy lives in `dist/apollo-media-card.js`. Add this GitHub repository to HACS as a custom **Dashboard** repository. HACS can then manage card updates from Git instead of manually copying JavaScript into Home Assistant.

## Source of truth

Git is the canonical project history for AMS, the Kodi add-on, the Apollo Media Card, tests, release metadata, and distribution files. `scripts/build-kodi-repository.py` rebuilds Kodi repository metadata from the checked-in add-on source, and `scripts/verify-project.py` verifies the published repository artifacts.
