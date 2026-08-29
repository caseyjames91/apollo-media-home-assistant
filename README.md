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
