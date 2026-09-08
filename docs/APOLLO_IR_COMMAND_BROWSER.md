# AVA Devices & Commands browser

Apollo IR Server 0.4.0 and AVA Bridge 0.10.0 add the first real command browser.

## Device command list

Selecting a device now renders the commands Apollo has recorded for that
device. Each row shows:

- command name
- IR or RF type when known
- a `Test` button

## Test command

The per-command Test button calls Apollo IR Server `/api/send`, which sends the
stored Home Assistant/BroadLink command through `remote.send_command`.

Newly learned commands now also record the learner `remote.*` entity in Apollo's
metadata so command replay remains tied to the BroadLink remote that learned it.

For commands recorded before Server 0.4.0, AVA falls back to the currently
selected learner.

## Scope

This release intentionally does not rename or delete commands yet. The browser
and reliable per-command testing are established first so rename/delete can be
added on top of a proven command list.
