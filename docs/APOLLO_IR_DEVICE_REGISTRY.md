# Apollo IR device registry

Apollo IR Server 0.3.0 adds its own persistent device/command registry in the
add-on config directory.

This is intentionally separate from Home Assistant's BroadLink `.storage`.
Apollo does not scrape or depend on Home Assistant private storage internals.

## Existing BroadLink devices

Home Assistant does not expose a supported API that enumerates BroadLink's
stored device/command names. Existing device names can therefore be registered
once in the AVA UI with **Add existing device**. This does not relearn or alter
the existing BroadLink command data; it simply teaches Apollo the stable device
identifier so new commands can be learned into that same device namespace.

## New commands

Every successful Apollo learning job automatically records the device, command,
type (IR/RF), and learning timestamp in Apollo's registry.

## API

- `GET /api/devices`
- `POST /api/devices`
- existing `POST /api/learn` updates the registry on success
