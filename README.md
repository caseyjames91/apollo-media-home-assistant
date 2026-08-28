# Apollo Media Home Assistant

Home Assistant add-on repository for **Apollo Media Server**, the central catalog, profile, progress, and device-state service for Apollo Media.

Current release: **0.1.5**

Apollo stores application timestamps in UTC and renders user-facing server timestamps in the browser/device local timezone. The add-on currently uses SQLite in persistent Home Assistant add-on storage.

## Development releases

After uploading a future `Apollo-HA-Addon-X.Y.Z-update.zip` to the repository root, run:

```bash
./release-update.sh Apollo-HA-Addon-X.Y.Z-update.zip
```

The helper validates the tree/archive, applies the update, stages it, verifies the diff, commits the version, and pushes `main`.
