# Apollo IR learning API

The AVA app is the preferred learning UI. Home Assistant remains the backend
and performs learning through a configured `remote` entity such as BroadLink.

All endpoints require normal Home Assistant bearer-token authentication.

## Start learning

`POST /api/apollo_ir/learn`

```json
{
  "learner_entity_id": "remote.broadlink_rm4_pro",
  "device": "bedroom_ped_fan",
  "command": "power",
  "command_type": "ir",
  "timeout": 30
}
```

`command_type` is `ir` or `rf`.

The request returns immediately with HTTP 202 and a learning job. Home
Assistant runs `remote.learn_command` in the background.

## Read status

`GET /api/apollo_ir/jobs/{job_id}`

Terminal states:
- `learned`
- `timeout`
- `error`
- `cancelled`

The first implementation intentionally reports reliable start/completion
feedback rather than scraping BroadLink notifications or Home Assistant
`.storage` internals for RF sub-stage information.

## Learner discovery

`GET /api/apollo_ir/learners`

Returns Home Assistant remote entities available to the AVA setup UI.

## Security

The AVA stores its Home Assistant URL, selected learner entity, and access
token in Android private app preferences. The API uses Home Assistant's normal
authenticated HTTP view mechanism. No unauthenticated HA management endpoint
is added.
