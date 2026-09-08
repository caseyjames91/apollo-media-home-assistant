# Apollo IR Manager 0.11.0

This release expands the AVA Devices & Commands browser into a management UI.

## Commands
- Search/filter commands locally.
- Test from the command row.
- Overflow menu for Test and Delete.
- Delete calls Home Assistant `remote.delete_command` first.
- Apollo metadata is removed only after Home Assistant succeeds.
- Last-used metadata updates after successful sends.

## Devices
- Device dropdown shows command count and optional room.
- Refresh reloads the Apollo registry.
- Create remains separate.
- Manage selected device opens an Apollo-styled modal.
- Assign or clear a room.
- Delete empty devices.
- Delete a device and all commands with confirmation.

## RF
RF learning messaging is clearer, but Apollo does not claim to expose
BroadLink's internal frequency-found substage because Home Assistant's public
remote service does not provide that telemetry.

## Local AVA emitter routing
Not implemented in this release. Home Assistant's public BroadLink learning
service does not return the raw learned IR payload, so arbitrary learned IR
commands cannot yet be replayed through the AVA emitter without importing the
payload or changing learning ownership.
