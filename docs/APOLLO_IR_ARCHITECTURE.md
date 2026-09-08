# Apollo IR / RF Architecture

Apollo IR follows the same Home Assistant Supervisor add-on distribution model
as Apollo Media Server.

## Components

- **BroadLink RM4 Pro** — IR/RF learner and optional transmitter.
- **Apollo IR Server add-on** — Home Assistant backend. Calls HA's `remote`
  services through the Supervisor Core API and owns learning-job state.
- **AVA IR Bridge app** — preferred user interface for learning plus room-local
  Android `ConsumerIrManager` IR transmission.
- **Home Assistant** — automation/orchestration substrate; normal users do not
  need to open its UI to teach commands.

## Installation model

The existing GitHub repository is already an Apollo Home Assistant add-on
repository. Apollo IR Server is another add-on folder beside
`apollo_media_server`, so it is installed and updated from the same custom
repository in the Home Assistant Add-on Store.

This intentionally replaces the earlier `custom_components/apollo_ir`
prototype. Apollo IR does not require manually copying Python files into
`/config/custom_components`.

## AVA learning flow

AVA -> Apollo IR Server:8100 -> Home Assistant Supervisor Core API ->
`remote.learn_command` -> BroadLink.

The add-on reports learning completion to the AVA. AVA never reads Home
Assistant `.storage` files and does not require a HA long-lived token.

## AVA emission

AVA continues to provide:

- `POST /ir/raw`
- `POST /ir/broadlink` (migration compatibility)

Room-local IR transmission is native Android `ConsumerIrManager`.
