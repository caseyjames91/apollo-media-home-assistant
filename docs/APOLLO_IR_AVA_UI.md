# AVA learning UI

AVA Bridge 0.7.0 removes manual Home Assistant entity-ID entry from the normal
learning workflow.

## Learner selection

The app requests `/api/learners` from Apollo IR Server and presents Home
Assistant `remote` entities in a dropdown. The previously selected learner is
remembered across launches.

## Learning result

A successful job presents a clear `✓ Learned` result with device and command
name.

## Test after learning

Apollo IR Server 0.2.0 adds `POST /api/send`, which proxies
`remote.send_command` through the Supervisor Core API. After a successful
learning job, AVA displays `Test Last Learned Command` so the user can verify
the newly taught command without opening Home Assistant.
