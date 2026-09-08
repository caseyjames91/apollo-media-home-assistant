# Apollo IR Server

Apollo IR Server is the Home Assistant add-on backend for Apollo AVA remotes.

It uses Home Assistant's Supervisor Core API to call the existing `remote`
integration, including BroadLink `remote.learn_command`, while the AVA remains
the user-facing learning interface.

## Network API

Default port: `8100`

- `GET /status`
- `GET /api/learners`
- `POST /api/learn`
- `GET /api/jobs/{job_id}`

If `api_key` is configured in the add-on options, AVA clients send it in the
`X-Apollo-IR-Key` header.

The add-on does not require a Home Assistant long-lived access token. It uses
the Supervisor-provided token internally.
