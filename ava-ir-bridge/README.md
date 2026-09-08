# AVA IR Bridge 0.3.0

Generic native Android IR bridge for the AVA Home Remote (RX1, Android 11).

## What changed

- Removed all hard-coded device commands and learned IR codes from the APK.
- Home Assistant (or another trusted LAN client) supplies the BroadLink learned Base64 code at transmit time.
- Kept one generic endpoint: `POST /ir/broadlink`.
- Optional carrier override: `POST /ir/broadlink?carrier=38000`.
- Added a persistent prototype signing key so future builds from this project can use `adb install -r`.

## Generic transmit

```bash
curl -X POST \
  -H 'Content-Type: text/plain' \
  --data-binary 'Jg...' \
  http://AVA_IP:8765/ir/broadlink
```

Or specify the carrier frequency:

```bash
curl -X POST \
  -H 'Content-Type: text/plain' \
  --data-binary 'Jg...' \
  'http://AVA_IP:8765/ir/broadlink?carrier=38000'
```

## Status

```bash
curl http://AVA_IP:8765/status
```

## Build

```bash
./build-on-apollo-server.sh
```

### First install of 0.3.0

0.2.0 was built with a transient Docker debug key, so Android will reject 0.3.0 as an update. Uninstall once:

```bash
adb uninstall com.apollo.avairbridge
adb install app/build/outputs/apk/debug/app-debug.apk
```

Starting with 0.3.0, this project carries a stable prototype signing key. Future builds from this project should update normally with:

```bash
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

## Security

This prototype has no HTTP authentication. Keep TCP 8765 on a trusted LAN only.
