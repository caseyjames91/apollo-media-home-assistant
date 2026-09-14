# CURRENT AUTHORITATIVE CHECKPOINT — 2026-09-13

## Production-copy migration compatibility validated

Branch: `feature/apollo-integrations`

Latest functional checkpoint: `6e0fe8fdb7b8261f44aee802fe09fed2d0869230` — `Preserve legacy integration visibility`

Previous Android TV stable-identity functional checkpoint:
`a1e82d6016448bd16107a9a67df2d830eaec4e08` — `Use stable Android TV certificate identity`

Previous handoff checkpoint:
`3f1285572947cd50571a6f58662304c1e913d160` — `Checkpoint Android TV stable identity validation`

Main baseline remains:
`916bf7d5a6085c6ba6709b4230fbb49d964ed142` — `Release Apollo Media 0.10.64`

### Production database migration test

A transactionally consistent backup of the live AMS 0.2.29 Home Assistant add-on database was created using SQLite's online backup API.

Production snapshot before feature-branch migration:
- integrations: 4
- devices: 2
- rooms table: absent
- profiles: 1
- media: 8001
- progress: 18
- playback_sessions: 1
- integrity_check: `ok`

Persisted integrations before migration:
- jellyfin
- radarr
- sonarr
- tmdb

Persisted devices before migration:
- Bedroom Kodi
- Kodi Test PC

The feature branch was run against a disposable working copy only. Production AMS and the source production snapshot were not modified.

### Migration result

After `init_db()` from `feature/apollo-integrations`:
- integrity_check remained `ok`
- all existing row counts were preserved
- `rooms` table was created successfully with 0 rows
- new integration columns were added
- new device columns were added
- both legacy Kodi devices remained present with their existing IDs, device keys, HA entity IDs, and enabled state
- AMS started successfully against the migrated copy on port 18101
- `/devices` returned both legacy Kodi devices
- `/rooms` returned `[]`
- `/integrations/types` returned the generalized integration registry

### Compatibility issue discovered and fixed

The first production-copy API check exposed a regression:

The database still contained all 4 integrations, but `GET /integrations` returned only:
- radarr
- sonarr
- tmdb

Jellyfin was hidden because:
1. `jellyfin` was not registered in the new generalized integration registry, and
2. `GET /integrations` filtered out persisted rows whose kind was absent from the registry.

This was fixed by:
- registering `jellyfin` as a first-class integration type
- marking Jellyfin as requiring `base_url` and `access_token`
- changing `GET /integrations` so persisted configuration rows remain visible even if a future/legacy kind lacks a registry entry
- adding regression tests so unknown persisted integration kinds are not silently hidden

Revalidation against the migrated production copy now returns:
- jellyfin
- radarr
- sonarr
- tmdb

All four production integrations are API-visible.

### Current Android TV state

Android TV remains fully real-hardware validated for:
- discovery
- stable certificate MAC identity
- legacy host identity migration
- pairing
- persistent controls
- power
- navigation
- volume
- media controls
- app-link launch
- offline detection
- automatic reconnect
- same-device identity across endpoint changes

Bedroom Google TV stable identity:
- Apollo UUID: `008f7ebb-a90d-4f02-9cad-410dec195ebc`
- source ID: `mac:b8:7b:d4:f1:f3:88`
- certificate MAC: `B8:7B:D4:F1:F3:88`

### Remaining merge gates

Before merging `feature/apollo-integrations` to main:

1. Exercise room CRUD and room/device assignment against the migrated production copy.
2. Exercise Radarr/Sonarr/TMDB integration tests against the migrated production copy.
3. Verify Jellyfin configuration remains intact and its existing sync/media paths still work.
4. Decide and implement/document meaningful Android TV integration `/test` behavior (currently placeholder).
5. Run final full suite and clean-tree check.
6. Update handoff with final migration/runtime proof.
7. Merge to main.
8. Only after Android TV/integration architecture is merge-ready, move to Apollo second-screen UI implementation.

---

# CURRENT AUTHORITATIVE CHECKPOINT — 2026-09-13

## Android TV stable identity — real-hardware validated

Branch: `feature/apollo-integrations`

Functional/code checkpoint: `a1e82d6016448bd16107a9a67df2d830eaec4e08` — `Use stable Android TV certificate identity`

Previous documentation checkpoint: `f5916281e4e2e5c76d09a18e54c9db7f2a6641dd` — `Clarify integration checkpoint HEAD`

Main baseline remains: `916bf7d5a6085c6ba6709b4230fbb49d964ed142` — `Release Apollo Media 0.10.64`

Released versions at baseline:
- Kodi addon: `0.10.64`
- AMS: `0.2.29`

### What changed

Android TV discovery no longer treats `host:port` as durable device identity when the Remote v2 TLS certificate identity can be read.

The integration now:
- probes the Android TV Remote v2 pairing TLS endpoint
- reads the certificate device name and MAC using `androidtvremote2.async_get_name_and_mac()`
- normalizes the MAC
- uses `mac:<lowercase-colon-mac>` as stable `source_device_id`
- retains host/port in device `config_json` as mutable connection metadata
- exposes `mac`, `certificate_name`, and `stable_identity` in discovery results
- falls back to legacy `host:port` discovery identity only when certificate identity cannot be read, with `stable_identity=false`

### Legacy migration behavior

Existing Android TV rows that were imported before stable identity support are migrated in place when:
- the new import carries a MAC-based source identity, and
- exactly one existing row in the same integration matches the legacy `host:port` endpoint and saved config endpoint.

Migration updates:
- `source_device_id`
- `device_key`
- mutable connection metadata

Migration preserves:
- Apollo device UUID
- room assignment
- Apollo friendly/custom name
- integration association
- pairing relationship / integration credentials

This prevents DHCP/IP changes from creating duplicate Apollo devices.

### Real discovery results

Physical discovery on the test network returned stable certificate identity for all three Android TV devices:

- Bedroom Google TV
  - host: `10.10.10.85`
  - certificate name: `Google TV Streamer`
  - certificate MAC: `B8:7B:D4:F1:F3:88`
  - source ID: `mac:b8:7b:d4:f1:f3:88`

- Living Room Google TV
  - host: `10.10.10.59`
  - certificate name: `Google TV Streamer`
  - certificate MAC: `FC:91:5D:DF:F6:22`
  - source ID: `mac:fc:91:5d:df:f6:22`

- Living Room Shield
  - host: `10.10.10.157`
  - certificate name: `SHIELD Android TV`
  - certificate MAC: `48:B0:2D:30:F0:D9`
  - source ID: `mac:48:b0:2d:30:f0:d9`

All three returned `stable_identity=true`.

### Bedroom Google TV real migration validation

Existing Apollo device before migration:
- Apollo UUID: `008f7ebb-a90d-4f02-9cad-410dec195ebc`
- source ID: `10.10.10.85:6466`
- integration ID: `87278247-91e7-420f-8511-487aa20c8324`
- paired: true

Imported stable identity:
- `mac:b8:7b:d4:f1:f3:88`

Observed after migration:
- Apollo UUID remained `008f7ebb-a90d-4f02-9cad-410dec195ebc`
- exactly one matching device row existed
- `device_key` updated to:
  `android_tv:87278247-91e7-420f-8511-487aa20c8324:mac:b8:7b:d4:f1:f3:88`
- source ID updated to:
  `mac:b8:7b:d4:f1:f3:88`
- host remained `10.10.10.85`
- paired remained true
- state returned `available=true`
- state reported Google TV Streamer device info
- HOME command returned HTTP 204 and worked

This proves the real path:

`legacy IP identity -> stable certificate MAC identity -> same Apollo UUID -> same pairing -> same control -> no duplicate`

### Android TV status

The Android TV integration has now been validated for:
- registry/type exposure
- mDNS discovery
- stable certificate identity
- legacy identity migration
- pairing
- persistent control connection
- capability profile
- navigation
- volume
- media controls
- power off/wake
- app-link launch
- physical offline detection
- native reconnect after return
- command rejection while unavailable
- no-repair recovery
- host-independent Apollo device identity

### Remaining Android TV merge gates

Before merging `feature/apollo-integrations` to main:

1. Production-like migration validation against a copy of the real HA add-on database.
2. Verify legacy Kodi/device/integration rows survive migration/startup.
3. Verify Radarr/Sonarr/TMDB integrations still behave correctly.
4. Verify room CRUD and room/device relations.
5. Verify Android TV integration config on the copied production DB.
6. Decide whether to replace/document the current placeholder Android TV integration `/test`.
7. Run full suite and ensure clean tree.
8. Merge to main only after the copied-production-database gate passes.

Second-screen Apollo UI work remains intentionally after Android TV merge-readiness.

---

# CURRENT AUTHORITATIVE CHECKPOINT — 2026-09-13
## Checkpoint — Apollo integration foundation + Android TV end-to-end runtime validation

> **READ THIS FIRST.** This checkpoint supersedes older current-state and next-task statements later in this file. Historical checkpoints are intentionally preserved below.

### Repository state

- Active development branch: `feature/apollo-integrations`
- Functional/code checkpoint: `63060c2 — Track Android TV availability and reconnect natively`
- Full functional checkpoint SHA: `63060c2d86929cdad033adf0a44aa9616372493c`
- Handoff/documentation commit layered directly on top: `9116a89 — Checkpoint Android TV integration runtime validation`
- Expected branch HEAD immediately after this handoff: `9116a89`

### Why the checkpoint SHA differs from branch HEAD

The functional/code checkpoint described by this handoff is `63060c2 — Track Android TV availability and reconnect natively`.

After that functional commit was created and runtime-validated, `PROJECT_HANDOFF.md` was updated and committed separately as `9116a89 — Checkpoint Android TV integration runtime validation`. Therefore `9116a89` is expected to be the branch HEAD even though the code state being documented is `63060c2`.

`9116a89` has `63060c2` as its direct parent. No Apollo source or runtime behavior changed between those commits; `9116a89` only updates `PROJECT_HANDOFF.md`.

This difference is intentional and must not be interpreted as repository drift. When resuming Apollo, if `feature/apollo-integrations` is at `9116a89`, the repository is exactly at this checkpoint. If HEAD is newer, inspect commits after `9116a89` to determine what work occurred after this handoff.
- Current `origin/main` baseline: `916bf7d — Release Apollo Media 0.10.64`
- Full `origin/main` SHA: `916bf7d5a6085c6ba6709b4230fbb49d964ed142`
- Working tree at checkpoint creation: **clean**
- This branch is a **temporary development/safety branch**, not a long-lived fork or separate Apollo product line.
- Intended flow remains: build integration architecture → runtime-test it → validate migration compatibility → merge to `main` → continue normal Apollo development.
- Kodi stable/runtime baseline inherited from main: **0.10.64**
- AMS released/runtime baseline inherited from main: **0.2.29**

### Why this checkpoint exists

Apollo has crossed a major architectural boundary.

The project now has a generalized integration/device/room foundation and the first real implementation, **Android TV**, has been proven against physical hardware through discovery, import, pairing, state, navigation, media controls, volume, power, app-link launching, true offline detection, and automatic recovery.

This is a good recovery point because the next work changes from “prove the Android TV control stack works” to “harden identity/migration and prepare the branch for merge.”

### Binding integration architecture

Apollo's device architecture now follows this rule:

**Integrations own how devices are discovered and controlled. Apollo owns how those devices are organized and presented.**

Three layers:

1. **Integration type / driver**
   - examples: `android_tv`, future `home_assistant`, `ir_remote`, `kodi`, Roku, Sonos, AVR integrations, etc.
2. **Configured integration instance**
   - stores driver-specific shared configuration and credentials.
3. **Apollo device**
   - one discovered/imported physical or logical device belonging to an integration instance.
   - Apollo owns friendly name, room assignment, capabilities, presentation, and shared configuration metadata.

Current Android TV design intentionally uses **one Android TV integration instance for multiple TVs**. Each TV is its own Apollo Device and is paired/trusted individually while sharing the integration's client identity/certificate material.

### Binding configuration/control ownership rule

The agreed model is hybrid:

- **AMS/backend is authoritative for configuration**
  - integrations
  - imported devices
  - friendly names
  - Apollo room assignments
  - capabilities
  - shared connection/configuration metadata
- **Remote clients may cache configuration locally**
  - fast UI
  - resilience if AMS is briefly unavailable
- **Integration drivers decide the control path**
  - Android TV may ultimately be controlled directly from a remote/client where appropriate
  - IR stays local when local IR hardware owns emission
  - HA-origin devices may be controlled through Home Assistant
  - AMS remains authoritative for centralized/profile/shared state

Binding rule:

**AMS owns configuration. The integration driver decides the control path.**

Do not make Home Assistant special in the architecture. HA is a later integration/discovery/control source, not the owner of Apollo rooms or devices.

### Integration/device/room foundation completed on this branch

Key feature history:

- `b027fa8 — Add Apollo integration device room foundation`
- `4ff9692 — Add Android TV integration registry and discovery`
- `f349b04 — Add Android TV pairing and control`
- `7247ec5 — Keep Android TV control connections persistent`
- `1c18c5c — Expose capability-driven device controls`
- `64996fbf — Add Android TV reconnect recovery and device deletion`
- `d0dac7b — Flush Android TV app launch commands`
- `63060c2 — Track Android TV availability and reconnect natively`

Foundation now includes:

- generalized Integration model/registry
- Apollo-owned Room model/API
- generalized Device model/API
- additive SQLite migration support
- Android TV integration type
- Android TV Remote v2 discovery
- import into Apollo Devices
- pairing
- persistent control connections
- generic capability-driven control profiles
- device deletion
- connection cleanup
- app-link launch flush handling
- native connection availability/reconnect lifecycle

### Android TV protocol/runtime choice

Android TV uses:

- Python package: `androidtvremote2==0.3.2`
- protocol family: Android TV Remote protocol v2
- normal runtime does **not** require ADB
- pairing port: 6467
- remote/control port: 6466

ADB was used only as a diagnostic tool while investigating Kodi/package-launch behavior. Do not make ADB a normal Apollo Android TV runtime dependency unless that product decision is deliberately changed later.

### Physical hardware runtime target

Primary test device:

- Apollo name: **Bedroom Google TV**
- Hardware identified by Remote v2: **Google TV Streamer**
- Manufacturer: **Google**
- Test host during this checkpoint: `10.10.10.85`
- Remote v2 endpoint during this checkpoint: `10.10.10.85:6466`
- Apollo device UUID: `008f7ebb-a90d-4f02-9cad-410dec195ebc`
- Android TV integration UUID used by the temporary test DB: `87278247-91e7-420f-8511-487aa20c8324`

Other devices discovered during real discovery:

- Living Room Google TV — `10.10.10.59:6466`
- Living Room Shield — `10.10.10.157:6466`

These addresses are runtime observations, **not stable identities**.

### Real Android TV discovery/import/pairing validation — PASSED

Real mDNS discovery through `_androidtvremote2._tcp.local.` found all three Android TV devices listed above.

Bedroom Google TV was imported successfully as an Apollo Android TV device.

Real Remote v2 pairing succeeded on the physical Google TV Streamer.

Post-pairing state was read successfully and returned:

- available: true
- power state
- foreground app
- volume level/max/mute
- manufacturer
- model
- software version

This proves the integration is not a mocked-only implementation.

### Persistent-control lifecycle — PASSED

The first implementation connected/disconnected around each individual command. Real hardware exposed that as unreliable: HTTP 204 only proved AMS accepted the request; the first Remote v2 command could be lost during connection startup.

The implementation was changed to **one persistent Remote v2 connection per paired Apollo device**.

Current behavior:

- connection cached by Apollo device UUID
- per-device async lock serializes operations
- fresh connection receives a short 0.5-second initial settle period
- normal button presses reuse the established connection
- no reconnect between normal rapid commands
- connection closed on AMS shutdown, device deletion, pairing restart, or explicit lifecycle reset

Real hardware validation:

- HOME succeeds after initial connection settle
- 3× DPAD_DOWN at approximately 150 ms spacing all executed
- DPAD_DOWN → DPAD_RIGHT → DPAD_RIGHT at approximately 300 ms spacing was reported **flawless**
- no reconnect occurred between those button presses

### Capability-driven control profile — PASSED

Apollo exposes a generic device control profile so future UI/second-screen clients do not need to hardcode Android TV semantics.

Current Android TV control groups:

**power**
- POWER

**navigation**
- DPAD_UP
- DPAD_DOWN
- DPAD_LEFT
- DPAD_RIGHT
- DPAD_CENTER
- BACK
- HOME

**volume**
- VOLUME_UP
- VOLUME_DOWN
- MUTE

**media**
- MEDIA_PLAY
- MEDIA_PAUSE
- MEDIA_PLAY_PAUSE
- MEDIA_STOP
- MEDIA_PREVIOUS
- MEDIA_NEXT

Android TV also advertises:
- launch support
- state support

This is the contract the future Apollo second-screen/device UI should consume.

### Real physical controls validated

Successfully exercised on the Bedroom Google TV Streamer:

- HOME
- DPAD_DOWN
- DPAD_RIGHT
- rapid navigation sequences
- DPAD_CENTER
- BACK
- VOLUME_UP
- VOLUME_DOWN
- MUTE
- MEDIA_PLAY_PAUSE
- POWER off
- POWER wake/on
- app-link launch using YouTube

Power behavior is especially important:

1. POWER turned the physical TV/streamer off.
2. Remote v2 state remained connected enough to report:
   - available: true
   - is_on: false
3. A second POWER woke/turned the device back on.
4. No AMS restart or re-pair was required.

Not individually runtime-tested at this checkpoint, but using the same validated key path:
- DPAD_UP
- DPAD_LEFT
- MEDIA_PLAY
- MEDIA_PAUSE
- MEDIA_STOP
- MEDIA_PREVIOUS
- MEDIA_NEXT

Do not treat those untested individual keys as a blocker unless a regression appears.

### App launching — normal/deep-link path PASSED

A Remote v2 app-launch issue was traced to library behavior.

`androidtvremote2.send_launch_app_command()` buffers the launch message asynchronously. AMS originally returned too quickly, so the buffered write could fail to reach the TV reliably.

The fix adds a brief 0.1-second event-loop flush after sending app-launch requests.

Real physical validation:

- `https://www.youtube.com` successfully opened YouTube through AMS.

Known platform limitation:

- plain package launch for Kodi (`org.xbmc.kodi`) did not work through Remote v2.
- direct package launch also failed in the same way outside AMS.
- the user's Unfolded Circle Remote 2 test also failed to open Kodi by package.
- ADB diagnostics proved Kodi itself is healthy and launchable via its Android launcher activity.
- therefore this is not currently treated as an Apollo-specific failure.

Deferred:
- Apollo TV Launcher/helper APK for arbitrary installed-app/package launching
- installed-app enumeration

Do **not** block the Android TV integration milestone on Kodi package launching.

### Native offline detection and reconnect — REAL HARDWARE PASSED

A critical runtime test physically removed power from the Bedroom Google TV Streamer.

Before the final fix, AMS incorrectly behaved like this:

- `GET /state` returned stale cached state with `available:true`
- HOME returned HTTP 204 even though the TV was physically offline

Root cause:

- cached Remote v2 properties did not prove the TCP/TLS connection was alive
- key/app sends are buffered and therefore may not synchronously raise when the socket has disappeared
- AMS was maintaining its own coarse `connected` flag instead of using the library's native availability lifecycle

Final implementation uses `androidtvremote2`'s own connection lifecycle:

- `add_is_available_updated_callback(...)`
- `keep_reconnecting()`
- native socket-loss detection
- native reconnect loop with backoff
- callback-driven availability state

Real offline test with the streamer physically unplugged returned:

```json
{
  "available": false,
  "is_on": null,
  "current_app": null,
  "volume": null,
  "device_info": null
}
```

A HOME command while physically offline returned:

- HTTP **502 Bad Gateway**
- connection detail indicating the TV could not be reached at `10.10.10.85:6466`

This is the desired behavior. AMS no longer lies with stale state or false 204 success while the device is unavailable.

Then the physical streamer was plugged back in **without restarting AMS and without re-pairing**.

Recovered state returned:

- `available:true`
- `is_on:true`
- current app: Google TV launcher
- volume restored
- device info restored

A subsequent HOME command returned HTTP 204 again through the recovered connection.

Therefore the complete real hardware path is proven:

**online → physical disappearance → unavailable/502 → physical return → automatic reconnect → normal control**

This is a major Android TV integration runtime gate and should not be reopened without new regression evidence.

### Device deletion / cleanup

Apollo now has generic device deletion.

For Android TV devices:
- deletion closes/removes the cached persistent device connection
- pairing-session state for that device is removed
- the device DB row is deleted
- shared Android TV integration client credentials are retained because the integration may own other TVs

### Test status at this checkpoint

The Android TV integration work has repeatedly passed:

- targeted Android TV integration tests
- reconnect/availability tests
- device deletion tests
- capability-profile tests
- full AMS suite

Immediately before this handoff checkpoint, the reconnect/availability patch passed the targeted suite and full AMS suite after correcting a **test-only missing `CannotConnect` import**.

That temporary failure was not a production logic failure.

Expected full-suite count at this stage is approximately the high-60s; use the actual current test run rather than relying on an old count when making future release decisions.

Known non-blocking test warnings during this branch:
- Starlette TestClient/httpx deprecation
- anyio BlockingPortal deprecation
- occasional `.pytest_cache` permission warning

### Temporary Android TV AMS test runtime

Runtime validation has been performed with a separate test AMS so production Home Assistant add-on data is not modified.

Temporary AMS:
- URL: `http://127.0.0.1:18100`
- database: `/home/apollo/apollo-androidtv-test-runtime/config/apollo.db`
- data directory: `/home/apollo/apollo-androidtv-test-runtime/config`
- Python environment: `/home/apollo/apollo-androidtv-test-runtime/venv`

An unrelated existing Docker test service occupies port 18099:
- `ams-youtube-test`

Do not stop or overwrite that service merely to run Android TV tests. Port **18100** is the known-good Android TV temporary runtime port.

### Known remaining Android TV hardening work

#### 1. Stable device identity — NEXT

This is the next recommended task.

Current discovery/import identity is effectively:

`host:port`

Example:
`10.10.10.85:6466`

That is not sufficiently stable. A DHCP address change can make the same television appear to Apollo as a new device.

The `androidtvremote2` library can retrieve server certificate identity information through `async_get_name_and_mac()`. Investigate whether the certificate MAC/fingerprint provides a durable and sufficiently unique device identity for Apollo.

Requirements for the fix:

- preserve existing imported devices when possible
- do not silently duplicate a TV after IP change
- keep host/IP as mutable connection metadata, not identity
- handle devices where the certificate identity may be missing or unusual
- migration behavior for already-imported `host:port` Android TV devices must be explicit and safe

Do not use model name or friendly name alone as identity; those are not unique.

#### 2. Production-like migration validation

Before merging this branch to main:

1. back up/copy the production HA add-on SQLite DB
2. run the feature-branch AMS against the copy
3. verify additive schema migration
4. verify existing integrations remain intact
5. verify existing Kodi device registration behavior
6. verify ARR/TMDB integration behavior
7. verify room CRUD
8. verify Android TV configuration/import/pairing state
9. verify no destructive SQLite rebuild or data loss occurred

Production AMS normally uses:
- DB: `/config/apollo.db`
- port: 8099

Do not point experimental branch code directly at the only production DB copy.

#### 3. Android TV integration-level `/test`

The generic Android TV integration-level test endpoint may still be placeholder behavior.

Device-level pairing/state/control is real and runtime-proven, but before merge decide whether:
- integration-level `/test` should perform a meaningful validation, or
- the product intentionally treats device-level state as the connectivity test.

Do not cite the existing integration-level placeholder as proof of connectivity.

### Merge/release gate

Do **not** merge `feature/apollo-integrations` to main yet.

Recommended gate:

1. stable identity approach implemented or consciously deferred/documented
2. production-like SQLite migration validated against a copy of the actual production DB
3. legacy Kodi registration still works
4. existing ARR/TMDB integrations still work
5. Android TV discovery/import/pairing/control still works
6. real offline/reconnect behavior remains good
7. full AMS tests pass
8. working tree clean
9. handoff updated with final pre-merge SHA/state

After that:
- merge integration branch to `main`
- determine AMS release/version bump
- deploy through normal production path
- runtime validate production deployment
- then continue to second-screen implementation

### Product priority after Android TV

User explicitly established the order:

1. **Android TV first**
2. complete and harden the Android TV integration
3. then implement/apply the Apollo UI to the remote's second/bottom screen

Do not switch to Home Assistant as the next integration.
Do not jump into second-screen implementation before the remaining Android TV merge gate is satisfied.

### Second-screen direction retained

After Android TV is merge-ready, return to the Apollo remote UI.

Persistent header:
- hamburger at top-left
- active Room
- global Search
- Profile at top-right

Persistent bottom navigation.

Home:
- overview-oriented
- center content modeled after the Apollo HA card
- no redundant Quick Actions block

TV:
- What's On
- Guide
- DVR later

Devices:
- devices assigned to current Apollo room
- selecting a row opens device controls
- inline power action when capability exists
- control surface should be driven by the AMS capability profile, not Android-TV-specific hardcoding
- expose as many appropriate controls as possible on the second display

Media:
- Apollo-card-style carousel rails
- Trending / Popular Movies / Shows
- Watchlist
- See More → grid

Library:
- Recently Added / Released
- Shows / Movies walls
- sorting

YouTube:
- recommendations
- subscriptions
- channels
- history
- search

Global search:
- all media
- TV listings

Settings → Integrations remains the architecture/configuration hub.

### Deferred work

- Apollo TV Launcher/helper APK for arbitrary package launch
- installed Android TV app enumeration
- Home Assistant integration
- IR/remote integration
- additional TV/platform integrations
- production second-screen application work until Android TV branch is merge-ready

### Recovery procedure

When a new conversation starts:

1. Read this top checkpoint first.
2. Run:
   ```bash
   cd ~/apollo-media-home-assistant
   export GIT_PAGER=cat
   export PAGER=cat
   export LESS=FRX
   git status --short
   git branch --show-current
   git --no-pager log -5 --oneline
   git fetch origin
   ```
3. Confirm whether local `feature/apollo-integrations` and `origin/feature/apollo-integrations` are synchronized.
4. Compare repository history after `63060c2`.
5. Do not reconstruct the integration work from old conversation history unless Git differs from this checkpoint.
6. Resume with **stable Android TV device identity** unless newer commits/checkpoints say otherwise.
7. Preserve the no-pager preference for all future Apollo scripts/commands.

Desired recovery prompt remains:

**Resume Apollo.**

---

# CURRENT AUTHORITATIVE CHECKPOINT — 2026-09-08
## Checkpoint — Kodi 0.10.61 presentation validation + Estuary reference-client audit

- Branch: `main`
- Current repository HEAD before checkpoint: `6af4d28 Speed up AVA local volume repeat`
- `origin/main`: synchronized with local `main`
- Working tree before checkpoint: **clean**
- Installed/runtime-tested Kodi addon: **0.10.61**
- Kodi 0.10.61 functional commit: `5237473 — Improve Kodi skin presentation metadata`
- Kodi 0.10.61 release commit: `ce59dd5 — Release Apollo Media 0.10.61`
- Kodi 0.10.61 source gate: **90/90 passed**
- Kodi 0.10.61 is **runtime-tested but not stable-tagged**
- Last explicitly stable-tagged Kodi baseline remains **0.10.60**
- AMS runtime baseline remains **0.2.27**

### Repository state
Development continued on `main` after Kodi 0.10.61. Current HEAD before this checkpoint is AVA remote work. Do not assume the Kodi release commit is current HEAD.

### Kodi 0.10.61 runtime validation
Repository-installed Kodi 0.10.61 was confirmed on the headless Kodi client.

Runtime/visual validation established:
- Kodi-native movie/show/episode media types are exposed.
- IMDb/TMDb IDs are exposed where available.
- Poster, fanart and landscape roles render correctly.
- Episode thumb presentation prefers landscape/backdrop where appropriate.
- Arctic Fuse 3 renders Apollo Continue Watching correctly as a Landscape widget.
- Estuary consumes Apollo metadata, art, runtime, progress and canonical navigation correctly.

### Reference-client strategy
**Estuary is the Apollo reference client.**

Apollo-owned behavior should be complete and correct in stock Kodi before Fuse-specific presentation work is considered complete.

If Apollo behavior is wrong in Estuary, investigate Apollo first. If correct in Estuary but rendered differently in Fuse, investigate the skin/integration layer.

### Estuary audit
Validated:
- Apollo root navigation.
- Library Movies and Library Shows.
- Canonical show → season → episode navigation.
- Continue Watching mixed movie/episode presentation and progress.
- Watchlist → canonical title hierarchy.
- Discovery pagination / More Results.
- Native Kodi Search entry and canonical Apollo results.
- Profile progress rendering across entry points.

Next Up was empty for the current profile during this audit; previously runtime-validated behavior remains known-good.

Known presentation issue: Estuary shows `Sort by: Date` in places where Apollo already supplies meaningful ordering.

Historical/stale duplicate canonical records remain separate cleanup debt.

### Canonical media rule
Every Apollo title has one canonical media identity/navigation path.

Library, Search, Popular, Trending, Watchlist, Continue Watching, Next Up, recommendations and future feeds are entry points only. Selecting the same title from different entry points must resolve through the same canonical Apollo identity/path.

### Immediate product task
**Finish the Apollo experience in Estuary before returning to Fuse.**

Priorities:
1. Audit context-menu behavior against repository implementation.
2. Avoid redundant visible actions where possible without breaking Apollo explicit playback-intent semantics.
3. Improve misleading stock sort presentation where practical.
4. Improve deeper navigation/window labels only where useful and safe.
5. Final canonical movie/show/episode pass.
6. Preserve proven resume, bad-stream retry, Next Up and Watchlist behavior.

### Context-menu note
Playable Apollo items use `playable_media()` and Apollo supplies actions through `_play_context(...)`.

Kodi can independently add native resume/beginning behavior because Apollo exposes Kodi resume metadata. Duplicate-looking actions must therefore be investigated from source semantics before removal.

Next source inspection:
- `_play_context()`
- `_watchlist_context()`
- watched/unwatched actions
- Current Stream Info / Try Next Stream / Flag Current Stream
- beginning/local/manual-stream actions

Do not ask the user to paste implementation already available in the repository.

### Artwork direction
Preferred separation:
- AMS: canonical media and artwork needed by AMS/HA clients.
- Kodi artwork/enrichment layer: Kodi/Fuse-specific rich artwork when needed.
- Fuse: renderer consuming Kodi standard artwork roles.

Investigate TMDb Helper / Skin Info Service / Artwork Dump plugin-item enrichment before building a custom Kodi artwork bridge.

### Binding playback architecture
- Rooms own playback devices; profiles own viewing state.
- AMS owns personalized profile state.
- Kodi owns actual playback observations.
- Initiating client owns playback decisions.
- Kodi-origin playback may use Kodi native Resume/Beginning.
- Card-origin playback sends explicit intent.
- Bad-stream retries preserve original intent silently.
- Rejected streams must not mutate valid profile progress.
- Do not implement resume as visible start-at-zero then seek.
- Do not reopen the solved resume/bad-stream parent lifecycle chain without new evidence.

---

# CURRENT AUTHORITATIVE CHECKPOINT — 2026-09-06
## Checkpoint — Kodi 0.10.60 Watchlist + pagination runtime validation
- Checkpoint base HEAD before this handoff update: `04c5320 — Release Apollo Media 0.10.60`
- Branch: `main`
- Working tree before checkpoint update: **clean**
- Stable/runtime-tested Kodi: **0.10.60**
- Kodi release commit: `04c5320 — Release Apollo Media 0.10.60`
- Kodi Watchlist functional commit: `62780fc — Add Kodi profile Watchlist integration`
- Kodi pagination restoration commit: `8513e1a — Restore Kodi discovery pagination`
- AMS runtime: **0.2.27**
- AMS Watchlist functional commit: `c0edba5 — Add AMS profile watchlists`
- AMS release commit: `5ef8aa2 — Release AMS 0.2.27`
- Kodi source test gate for 0.10.60: **86/86 passed**
- AMS source test gate for 0.2.27: **39/39 passed**

### Kodi 0.10.60 runtime gate — PASSED
Repository-installed Kodi 0.10.60 was validated through the normal Apollo Media Repository update path.

Runtime validation proved:
1. Profile Watchlist is exposed in Kodi.
2. Movie Add to Watchlist works.
3. Movie Remove from Watchlist works and refreshes correctly.
4. Show Add to Watchlist works.
5. Selecting a watchlisted show enters the same canonical show/season navigation used elsewhere.
6. Episodes do not expose Watchlist actions.
7. Discovery pagination is restored.
8. `More Results` loads the next page successfully.
9. Search pagination preserves the existing query and loads additional results without prompting for the query again.
10. Playback lifecycle behavior was not changed by the pagination restoration.

### Canonical title/navigation rule
Every Apollo title has one canonical media identity/navigation path.

Binding semantics:
- Library, Search, Popular, Trending, Watchlist, Continue Watching, recommendations, and future feeds are entry points only.
- Selecting the same title from different entry points must resolve through the same canonical Apollo title identity/path rather than creating feed-specific copies.
- Watchlist membership references the canonical title; adding/removing Watchlist membership does not create or replace media identity.
- Preserve the canonical title/navigation path; Watchlist is an entry point, not a parallel media identity.
- Continue Watching and Next Up remain profile-state views over canonical media rather than alternate media identities.

### Watchlist architecture
Apollo owns persistent, profile-scoped Watchlist state.

Current binding semantics:
- Movies and shows only.
- Episodes are deliberately rejected.
- Seasons are not currently first-class Watchlist media.
- Per-profile membership.
- Add/remove are idempotent.
- AMS returns canonical metadata/artwork and local availability.
- Kodi consumes AMS Watchlist state rather than owning separate Watchlist state.
- External discovery providers do not own Watchlist membership.

Runtime AMS endpoints:
- `GET /profiles/{profile_id}/watchlist`
- `GET /profiles/{profile_id}/watchlist/{media_id}`
- `PUT /profiles/{profile_id}/watchlist/{media_id}`
- `DELETE /profiles/{profile_id}/watchlist/{media_id}`

### Pagination regression and fix
A rollback had removed previously-working pagination from Kodi discovery/search.

Known-good historical behavior was restored:
- Popular/Trending discovery accepts and forwards `page`.
- Search accepts and forwards both `query` and `page`.
- `More Results` advances to the next provider page.
- Search `More Results` preserves the original query.
- The provider/API page size behavior remains `len(rows) >= 20` before showing `More Results`.
- Library Movies/Shows were not changed; recovered historical pagination applied to discovery/search, not local-library full-list rendering.

The 0.10.60 source gate added regression coverage for:
- AMS discovery page parameter
- discovery pagination routing
- search pagination with query preservation

### Current known-good baseline
- Kodi **0.10.60** is the stable/runtime-tested TV client baseline.
- AMS **0.2.27** is the runtime-tested server baseline.
- Kodi Watchlist integration is runtime-proven.
- Discovery/Search pagination is runtime-proven.
- Persistent Next Up browsing remains runtime-proven.
- End-of-episode Up Next remains runtime-proven when Kodi `service.upnext` is installed/enabled.
- The 0.10.59 repository metadata drift that omitted `service.upnext` from generated `addons.xml` was corrected by the release tooling; 0.10.60 repository metadata is rebuilt from authoritative addon XML and preserves the dependency.
- Do not reopen the solved resume/bad-stream parent lifecycle chain without new regression evidence.

### Binding playback architecture
- Rooms own playback devices; profiles own viewing state.
- `Media.runtime_seconds` is canonical expected-runtime authority.
- `Progress.duration_seconds` is profile viewing state only.
- Kodi owns actual playback and reports validated observations to AMS.
- Initiating client owns playback decisions.
- Kodi-origin playback may use Kodi native Resume/Beginning.
- Card-origin playback should send explicit intent and must not unexpectedly put a decision dialog on the TV.
- Bad-stream retries preserve the original intent silently.
- Rejected playback must not mutate legitimate profile state.
- Do not implement resume as visible start-at-zero then seek.

### Immediate next product work
Current retained priorities:
1. **Investigate remote-stream startup latency regression**
   - measure AMS/provider/source resolution
   - Kodi parent-plugin resolution
   - source-session handling
   - resume metadata setup
   - remote duration validation
   - actual Kodi player open
   - do not assume the resume fix is the cause until measured

2. **Apollo branded playback splash/loading state**
   - backdrop immediately while resolving/opening
   - transparent logo when available, title fallback
   - continuous through bad-stream retries
   - dismiss on `onAVStarted()` or terminal failure
   - eventually compose with Ensure Kodi Ready

3. **Substantial Home Assistant card shared-client work**
   - card and Kodi remain separate full clients over shared AMS state
   - normal card browsing must not move the TV UI
   - `Show on TV` explicitly transfers card navigation context to Kodi
   - `Resume on Card` transfers Kodi navigation context back to the card

Retained roadmap:
- Ensure Kodi Ready lifecycle
- Recent Sessions / Resume Here
- Apollo Companion
- YouTube integration

### Recovery procedure
On a new conversation:
1. Read this checkpoint first.
2. Run `git status --short`.
3. Inspect `HEAD` and `origin/main`.
4. Compare Git history against this checkpoint.
5. Verify runtime versions when relevant.
6. Update this file after meaningful transitions.

Desired recovery prompt: **Resume Apollo.**

> **READ THIS FIRST.** This checkpoint supersedes older current-state/next-task statements later in this file. Historical investigation below is retained intentionally.

---

# CURRENT AUTHORITATIVE CHECKPOINT — 2026-09-05
## Checkpoint — Kodi 0.10.58 Next Up runtime validation

- Checkpoint base HEAD before this handoff update: `578a8c6634df682307855e364dce553ca3ab8cf3`
- Kodi release/runtime candidate: `0.10.58`
- AMS runtime: `0.2.26`
- Functional commit: `dcd7fcc — Add Kodi Up Next episode handoff`
- Release commit: `578a8c6 — Release Apollo Media 0.10.58`
- Kodi test gate: `77/77` passed before functional commit and again during release.
- Kodi 0.10.57 persistent Next Up browse/play runtime gate passed:
  - AMS Next Up rendered American Dad! S01E02 “Threat Levels”.
  - Selecting it played the correct episode through the canonical Apollo playback path.
  - Once partial progress existed, it disappeared from Next Up and appeared in Continue Watching.
- Kodi 0.10.58 end-of-episode Next Episode runtime gate passed after installing/enabling Kodi `service.upnext` on the headless test client:
  - Apollo/AMS resolved S01E03 “Stan Knows Best”.
  - Kodi log confirmed `[Apollo Media 0.10] Up Next prepared: S01E03 Stan Knows Best`.
  - Up Next displayed the near-end prompt.
  - Accepting the prompt started the successor correctly through Apollo.
  - End-of-episode handoff uses explicit Beginning intent.
- Initial no-prompt result was environmental, not an Apollo resolver failure: `service.upnext` was absent from the headless Kodi client. Installing it made the existing 0.10.58 integration work.

### New TODOs captured at this checkpoint

1. **Investigate remote-stream startup latency regression.**
   User observed that remote streams seem slower to start than before the resume/lifecycle fixes. Diagnose with timings across the full ownership chain before changing behavior: AMS/provider/source resolution, parent-plugin lifecycle, source-session handling, resume metadata setup, remote duration validation, and Kodi player open. Do not assume the resume fix itself is the cause until measured.

2. **Apollo branded playback splash/loading state.**
   When playback is requested, show the movie/show backdrop while Kodi resolves/opens the stream, preferably with transparent show/movie logo when available and text-title fallback. Keep the splash continuous across source resolution and bad-stream retry so Kodi intermediate/loading UI does not flash through. Dismiss on `onAVStarted()` or terminal failure. This should later compose with the planned Ensure Kodi Ready lifecycle so launch/resolution/retry feels like one continuous Apollo-owned starting state.

### Release gate

Kodi `0.10.58` has passed the intended Next Up runtime validation and is eligible for stable promotion. This checkpoint update and stable tag are the next release actions.

### Next product work

After stable promotion/checkpoint, proceed to AMS-owned Watchlist unless the user chooses to prioritize the startup-latency investigation or playback splash first.

> **READ THIS FIRST.** This checkpoint supersedes older current-state/next-task statements later in this file. Historical investigation below is retained intentionally.

## Current known-good state

- Branch: `main`
- Stable playback baseline commit: `8d0e8ea`
- Working tree at checkpoint: **clean**
- Stable Kodi: **0.10.56**
- Runtime-tested Kodi: **0.10.56**
- Stable tag: `stable/0.10.56`
- Kodi functional fix: `f7f8324 — Resolve remote playback handoff through Kodi`
- Kodi release: `533dd88 — Release Apollo Media 0.10.56`
- Stable promotion: `8d0e8ea — Mark Apollo Media 0.10.56 stable`
- Stable/deployed AMS: **0.2.25**
- AMS functional fix: `a1a552c — Make canonical runtime authoritative for progress`
- AMS release: `d6c3c81 — Release Apollo Media Server 0.2.25`

## Kodi 0.10.56 runtime gate — PASSED

Final Simpsons S01E01 test proved the complete remote-resume failure path:

1. Native Resume choice was preserved.
2. Known bad 30-second candidate opened.
3. Validator rejected and persistently flagged it `bad_stream`.
4. Source session advanced from index 0 to index 1.
5. Index 1 automatically opened.
6. Original fixed resume intent survived: `17.585 / 1395.008`.
7. Valid retry resumed without a second resume prompt or visible post-start seek.
8. Rejected candidate produced **no AMS progress write**.
9. The old `Playlist Player: skipping unplayable item ... play_remote` parent-lifecycle failure did not recur.

## Root cause fixed in 0.10.56

0.10.55 launched `PlayMedia(play_session_stream...,noresume)` from normal `play_remote()` while leaving the canonical parent invocation unresolved. Kodi later treated that parent as unplayable and killed child playback before the validator could persist rejection/advance.

0.10.56 makes normal playable `play_remote()` resolve the parent through Kodi to `play_session_stream` using `xbmcplugin.setResolvedUrl()`. Context-menu/RunPlugin and retry paths still use `PlayMedia(...,noresume)` where appropriate.

Positive resolved-stream resume uses `VideoInfoTag.setResumePoint(position, duration)`, **not numeric StartOffset**. Runtime proved this starts at the requested resume point without a visible seek.

## Binding playback architecture

- Rooms own playback devices; profiles own viewing state.
- `Media.runtime_seconds` is canonical expected-runtime authority.
- `Progress.duration_seconds` is profile viewing state, never canonical metadata authority.
- Kodi owns actual playback and reports validated observations to AMS.
- Initiating client owns playback decisions.
- Kodi-origin playback may use Kodi native Resume/Beginning.
- Card-origin playback should send explicit intent and must not unexpectedly put a decision dialog on the TV.
- Bad-stream retries preserve the original intent silently.
- Rejected playback must not mutate legitimate profile state.
- Transient source technical metadata must not own canonical title metadata.
- Do not implement resume as a visible start-at-zero then seek.

## AMS 0.2.25 — production validated

The historical `42` poisoned-duration bug is fixed.

Trusted TMDB/provider metadata -> `Media.runtime_seconds` -> validation authority.

Validated Kodi playback -> `Progress.position_seconds` / `Progress.duration_seconds` -> profile state.

Production metadata sync populated canonical runtime for `42` as 7680 seconds. A later correct ~7696-second Kodi playback was accepted and naturally repaired the previously poisoned profile progress.

Do not revisit this bug without new regression evidence.

## Resume implementation facts

Native playable invocation tokens established by runtime probing:

- `resume:true` = Kodi native Resume
- `resume:false` = Kodi native Beginning
- trust these as native choices only when plugin `HANDLE >= 0`

Source-session intent survives remote retries.

`noresume` remains intentional on transient `PlayMedia` handoffs/retries to prevent a second unrelated native resume dialog.

## Current priority

Kodi 0.10.56 + AMS 0.2.25 are the known-good stable playback baseline.

Do not reopen the solved resume/bad-stream lifecycle chain without new evidence.

Continue completing Apollo from this baseline. Retained roadmap includes:

- Ensure Kodi Ready lifecycle
- Home Assistant card shared-client/playback work
- Recent Sessions / Resume Here
- Apollo Companion Android MediaSession integration
- YouTube integration

## Recovery procedure

On a new conversation:

1. Read this checkpoint and the relevant historical sections below.
2. Run `git status --short`.
3. Inspect `HEAD` and `origin/main`.
4. Compare Git history against stable playback baseline `8d0e8ea`.
5. Inspect newer commits before changing source.
6. Verify runtime versions when relevant.
7. Update this file after meaningful transitions.

Desired recovery prompt: **Resume Apollo.**

## Handoff document status

The obsolete pre-0.10.56 live checkpoint has been removed from the active body.

Everything below `Historical Checkpoints and Decision Log` is retained only as development history and must not override the authoritative checkpoint above.

---

# Historical Checkpoints and Decision Log

This section intentionally preserves prior checkpoints, approaches, runtime failures, and superseded reasoning. Do not treat older “current state” statements below as current. They are retained so future sessions can see what was already tried and why later architecture changed.

Git history remains the ultimate record of source changes; this section is the human-readable development trail.

## Historical checkpoint — Apollo 0.10.46 stable

At this checkpoint:

- Stable release: **0.10.46**
- Runtime-tested Kodi version: **0.10.46**
- Release commit: `52f4a74 — Release Apollo Media 0.10.46`
- Stable-promotion commit: `adb4f49 — Mark Apollo Media 0.10.46 stable`
- Functional resume fix: `5ace03d — Preserve Kodi native resume choice for remote playback`

### Problem being solved

Apollo `_resolve_remote()` was injecting Apollo/AMS stored resume data into the resolved Kodi ListItem using:

- `ams.resume(...)`
- `tag.setResumePoint(...)`

This interfered with Kodi's native Resume / Start from beginning behavior for remote playback.

### 0.10.46 approach

The injected Apollo resume point was removed from `_resolve_remote()` so Kodi could own its native Resume / Start choice.

Runtime validation at the time confirmed:

- installed addon reported 0.10.46
- `_resolve_remote()` no longer called `ams.resume(...)`
- `_resolve_remote()` no longer called `tag.setResumePoint(...)`
- remote/debrid playback with saved progress was tested
- Resume worked
- Start from beginning worked

This was legitimately stable for the behavior under test, but later card/auto-resume requirements exposed that “leave resume entirely to Kodi” was not sufficient as the final cross-client architecture.

### Why this history matters

Do not blindly reintroduce positive AMS resume injection into the resolved transient stream ListItem. That was already shown to interfere with Kodi's native resume-choice behavior.

The later architecture instead requires explicit synchronization and clear separation between:

- canonical AMS profile state
- Kodi native bookmark state
- canonical browsed ListItem metadata
- transient playback-source identity
- requested playback intent

## Historical checkpoint — Apollo 0.10.47 watched-state fix

At this checkpoint:

- Stable Kodi release: **0.10.47**
- Runtime-tested Kodi version: **0.10.47**
- Kodi release commit: `4bfb85f64c21b50368c765b745051632d41ea4eb`
- Stable promotion commit: `b7d7fc5`
- AMS runtime version then: **0.2.23**
- AMS release commit: `8bd73320c8f6c4d88e1f9ab4a4686d7fa512939`
- Functional commit: `fc7aa6e — Make AMS authoritative for watched state`
- Stable manifest: `releases/stable/0.10.47.json`

### Watched-state architecture

AMS became authoritative for profile watched state.

API:

`PUT /profiles/{profile_id}/media/{media_id}/watched`

Kodi Apollo actions:

- Apollo: Mark watched
- Apollo: Mark unwatched

Runtime validation confirmed:

1. Apollo Mark watched updated AMS.
2. The title disappeared from Continue Watching after refresh.
3. Browsing to the title elsewhere rendered it watched.
4. Kodi → AMS mutation and AMS → Kodi rendering worked.

Kodi Omega still exposed its native `Mark as watched` context action in addition to Apollo's action. That was identified as a separate UX/integration issue rather than a reason to abandon AMS ownership.

### Deferred next problem from 0.10.47

A short RAR/error clip could technically play to completion and be treated as the real episode/movie, allowing bogus progress to mark the canonical title watched.

Required behavior established at that point:

- detect invalid playback
- skip/advance when possible
- persistently flag/quarantine the bad candidate
- invalid playback must not alter legitimate profile progress/resume/watched state
- avoid a simplistic short-duration rule that would reject legitimate short-form content

That work led into the 0.10.48 bad-stream validator.

## Historical checkpoint — bad-stream architecture, 0.10.48

Functional commit:

`64d8220 — Reject and quarantine invalid remote streams`

The chosen validation model was:

- Prefer comparison against canonical expected runtime.
- Accept ratios only when `0.50 <= actual / expected <= 1.75`.
- If no canonical expected runtime exists, only use a conservative obvious-error fallback: reject actual duration below 60 seconds.
- Flag invalid source with persistent `bad_stream`.
- Advance to the next candidate.
- Suppress rejected playback from updating legitimate profile state.

This was runtime-proven useful with Simpsons S01E01, where a short error clip was caught and skipped.

Later `42` testing proved why duration validation must remain: wrong-content playback may be a real playable video, including porn, rather than a tiny error clip. Source validation cannot be removed merely to make resume/progress updates easier.

## Historical checkpoint — canonical navigation restoration, 0.10.49

Functional commit:

`cdc3500 — Restore canonical show navigation`

Release:

`9111479 — Release Apollo Media 0.10.49`

The regression involved missing Kodi-side AMS discovery helpers, local-only Library routing, placeholder remote show playback, missing dispatch, and dead remote-pending behavior.

Runtime validated:

Popular/Trending → Show → Season → Episode

User confirmed seasons and episodes populate.

This established the binding rule that feeds are entry points, not owners of alternate title paths.

## Historical checkpoint — resume retry experiment, 0.10.50

Functional commit:

`efc2ee5 — Preserve resume intent across stream retries`

Release:

`a080499 — Release Apollo Media 0.10.50`

Approach:

- source session captured resume state
- service attempted to infer Resume vs Start choice
- retries used StartOffset
- beginning attempted `StartOffset="0"`

Test suite passed, but runtime disproved the approach:

`StartOffset="0"` did **not** suppress Kodi's native resume dialog on retry.

Do not retry this exact technique.

## Historical checkpoint — `noresume` retry experiment, 0.10.51

Functional commit:

`037f4ff — Suppress resume prompt on beginning retries`

Release:

`ce3527a — Release Apollo Media 0.10.51`

Approach:

- beginning retries used `PlayMedia(...,noresume)`
- fixed positive resumes retained StartOffset
- removed zero StartOffset

This improved prompt suppression but did not solve the underlying canonical-state problem.

The runtime investigation then exposed disagreement among Kodi's native bookmark, AMS profile state, and metadata attached to different plugin URLs.

## Historical checkpoint — AMS-authoritative resume experiment, 0.10.52

Functional commit:

`6a1a128 — Make AMS authoritative for playback resume`

Release:

`c39bda2 — Release Apollo Media 0.10.52`

Approach:

- source-session resume state came from canonical AMS progress
- positive resume became fixed StartOffset
- beginning/manual/retry paths used `noresume`
- explicit Play from beginning was added
- prior user-choice capture logic was removed

At the same time, canonical `playable_media()` was deliberately initialized with zero resume metadata:

- `tag.setPlaycount(0)`
- `tag.setResumePoint(0.0, 0.0)`

This was intended to avoid Kodi interfering with Apollo-managed resume.

### Runtime failure

Simpsons testing showed:

- explicit beginning worked
- bad stream could be skipped
- after valid playback, AMS contained real progress
- Kodi could still show `00:30`
- normal resume could still trigger unwanted dialog behavior

The initial interpretation that “Kodi only saved 30 seconds” was later proven wrong.

SQLite inspection showed Kodi's actual valid playback bookmark was correct. The 30-second display came from stale technical metadata attached to a different plugin identity.

This is a key dead end: do not treat the browsed ListItem's stale displayed duration as proof that Kodi's actual playback bookmark is wrong.

## Historical checkpoint — broader `noresume`, 0.10.53

Functional commit:

`e0820a2 — Suppress Kodi native resume for Apollo playback`

Release/current development HEAD at the later checkpoint:

`ff39f55 — Release Apollo Media 0.10.53`

Changes extended `noresume` to manual stream selection, retry paths, and service-driven rejection/advance.

An accidental broad replacement briefly removed `_resolve_remote()`'s `resume_mode` assignment and caused a `NameError`; it was restored before release. Full suite then passed.

Runtime:

- bad Simpsons error stream caught and skipped
- explicit beginning worked
- normal click started from beginning
- stale 30-second canonical display remained

This release was intentionally NOT promoted stable.

### Why 0.10.53 is not the final architecture

Suppressing dialogs is not equivalent to synchronizing state.

The user explicitly rejected an architecture where AMS “beats Kodi into submission.”

Final behavior must allow Kodi to know legitimate real progress and converge with AMS, while still preventing routine resume prompts when state is already synchronized.

## Historical discovery — Kodi and AMS were already numerically synchronized

Controlled Simpsons S01E01 test:

Stopped around 5:52.

AMS:

- position `350.906`
- duration `1395.008`

Kodi native bookmark:

- position `351.7`
- duration `1395.0`

Difference: about 0.8 seconds.

This disproved the idea that Kodi native progress necessarily had to be overwritten from AMS after playback.

Correct conclusion:

Kodi can persist legitimate player state and report it to AMS. Reconciliation should happen only for material drift/conflict.

## Historical discovery — stale 30-second UI was identity/metadata poisoning

Kodi SQLite showed:

Canonical `play_remote` file identity:

- streamdetails duration = 30 sec
- technical metadata belonged to the rejected error clip

Transient valid identity:

`play_session_stream&index=1`

- bookmark ≈ 351.7 / 1395
- streamdetails duration ≈ 1395
- valid HEVC stream

Kodi GUI while browsing Continue Watching showed the canonical `play_remote` URL and `ListItem.Duration=00:30`.

Therefore the 30-second value was stale technical metadata associated with the canonical plugin URL, not the valid resume bookmark.

This established the need to separate canonical title metadata from transient source technical metadata.

## Historical experiment — render AMS progress onto canonical ListItem

A runtime-only headless Kodi experiment applied AMS duration/resume to the browsed ListItem after retrieving progress.

Result:

- Simpsons changed from 00:30 to ~23:15
- progress indicator appeared correctly
- other Continue Watching titles also displayed realistic duration/progress

This proved AMS profile state can correctly drive canonical Apollo ListItem rendering.

It also proved that the deliberate zero-resume initialization in `playable_media()` was hiding legitimate state.

This runtime edit was diagnostic only and was not a release.

## Historical discovery — `42` poisoned profile state

Movie identity:

- title: `42`
- media UUID: `1e32b039-d78e-498f-9397-14d370f4ab3b`
- IMDb/canonical: `tt0453562`
- TMDB: `109410`

An earlier wrong remote stream was porn.

AMS retained:

- position ≈ 957 sec
- duration ≈ 1086 sec
- update timestamp Sep 1

Kodi also had an old canonical bookmark around 951 / 1086.

A later correct remote playback stopped around 37:50 and Kodi persisted:

- `play_session_stream&index=0`
- position ≈ 2265 sec
- duration ≈ 7695.7 sec

Kodi logs showed multiple AMS progress PUTs during that playback and on stop.

Yet AMS remained unchanged at the Sep 1 poisoned state.

Duplicate media identity was ruled out.

## Historical discovery — AMS returned success while rejecting progress

Kodi's AMS request helper uses `urllib.request.urlopen`, so non-2xx HTTP errors would raise.

Kodi's `[ApolloPerf] AMS PUT progress` therefore showed the server requests completed successfully.

Inspection of AMS `progress.py` explained the apparent contradiction:

rejected progress returns HTTP 200 with `changed:false`.

This is an observability problem as well as a validation problem. A future client improvement should surface/log `changed:false` so rejected writes do not look indistinguishable from accepted writes.

## Historical root cause — profile duration became a poison validator

AMS progress validation used:

`expected_duration = media.runtime_seconds or prior_profile_duration`

For `42`:

- `Media.runtime_seconds = 0`
- poisoned prior profile duration ≈ 1086 sec
- correct new duration ≈ 7696 sec
- ratio ≈ 7.09

AMS rejected the correct playback as implausible and returned `changed:false`.

This created a self-locking state:

bad playback duration accepted
→ stored in profile progress
→ reused as expected canonical duration
→ correct future playback rejected
→ poisoned profile can never self-repair

Architectural conclusion:

**Profile playback duration must never become canonical validation authority.**

## Historical root cause refinement — canonical movie runtime was never persisted

Live media API for `42` returned:

`runtime_seconds: 0`

Initial suspicion was that AMS lacked a movie-detail path.

Further source inspection refined that diagnosis.

`apollo_media_server/app/services/tmdb.py` already contains:

- `_movie_details(...)`
- a TMDB request to `/movie/{tmdb_id}`
- `sync_metadata()` calling `_movie_details()` for movies

But `_apply_movie()` only persists:

- tmdb_id
- year
- overview
- poster
- backdrop

It does **not** persist TMDB's movie `runtime`.

Therefore AMS already fetches the authoritative runtime during metadata sync but drops it instead of writing `Media.runtime_seconds`.

This is the immediate AMS metadata bug.

Do not build a redundant second TMDB detail client merely to obtain runtime. Reuse the existing detail/enrichment pipeline.

## Historical note — discovery route 404

A live request to:

`/discovery/movie/109410`

returned 404.

Inspection of discovery source confirmed there is no such movie-detail discovery route.

Popular/Trending-style discovery reconciliation persists list/feed metadata but not runtime.

This does not mean AMS lacks TMDB movie-detail capability; `services/tmdb.py` already has it through metadata synchronization.

## Historical note — AMS 10-second cutoff

Kodi's current reporting service emits periodically and on important playback events without its old position-minimum guard.

AMS `progress.py`, however, still contains:

`if position < 10: ... changed=False`

This was not responsible for the `42` failure because the test was far beyond ten seconds.

Review this policy separately. Do not confuse it with the duration-poison bug.

## Historical uncommitted normal-click experiment

At checkpoint `ff39f55`, the local working tree intentionally contains an unreleased Kodi change in:

- `kodi/plugin.video.apollomedia/main.py`
- `kodi/plugin.video.apollomedia/tests/test_resume_retry_intent.py`

The change routes normal `play_remote()` activation through:

`play_session_stream&index=N`

with `PlayMedia(...,noresume)`

rather than directly resolving the stream.

Its regression test passed.

Do not lose these changes, but do not assume they are the final solution either. They were created before the synchronization architecture was fully understood.

No 0.10.54 release should be created until the AMS runtime/progress authority problem is fixed and this Kodi change is reevaluated.

## Historical architecture decisions that remain binding

### Rooms vs profiles

**Rooms own playback devices; profiles own viewing state.**

### Canonical paths

Every title has one canonical media/navigation identity.

Feeds such as Continue Watching, Popular, Trending, Search, Library, and Recent Sessions are entry points, not alternate owners of titles.

### Addon and card

Kodi addon is a fully functional Apollo client.

Home Assistant card is another full Apollo client.

Normal card browsing must not move the TV UI.

Show on TV explicitly transfers card navigation context to Kodi.

Resume on Card transfers Kodi navigation context back to the card.

Card-origin playback calls into the addon rather than inventing a separate Kodi playback stack.

### Interaction ownership

Any required playback decision belongs on the client that initiated the operation.

Card-origin playback must not unexpectedly throw decision dialogs onto the TV.

### Resume synchronization

Desired end state:

- no progress → start
- synchronized Kodi/AMS state → auto-resume without routine prompt
- explicit beginning → start at zero
- material conflict → offer AMS/Kodi/beginning choices
- tiny drift → treat as synchronized

### Bad streams

Rejected playback must not mutate legitimate canonical profile state.

Actual stream duration remains important for validation.

### Canonical vs transient state

Do not conflate:

- canonical media metadata
- profile viewing state
- Kodi native bookmark
- canonical Kodi ListItem presentation
- transient source-session URL
- actual stream technical metadata
- playback intent

## Historical roadmap items retained from earlier checkpoints

### Ensure Kodi Ready

If Kodi is closed:

- invoke device-specific launch action
- wait for associated HA Kodi media_player to become ready
- continue the original operation
- expose visible Starting state

Apply consistently to Play, Resume, Play Locally, and remote playback.

### Apollo Companion

Lightweight Android companion layer:

- expose Kodi playback through native Android MediaSession
- provide lock-screen/system media controls
- relay controls to Home Assistant/Kodi
- remain an OS-integration layer, not the main Apollo UI

### Recent Sessions / playback handoff

Allow unfinished sessions from another room/device to appear in Apollo and offer Resume Here.

Preserve:

- canonical media identity
- position
- originating room/device
- recency
- useful source/resolution hints

Receiving room chooses the best source available there.

### YouTube integration

Future Apollo integration should support:

- browse
- recommendations
- playback
- profile awareness
- TV handoff
- minimal TV-side interaction

while fitting the same canonical/client architecture rather than becoming a separate UI silo.

## Runtime checkpoint — AMS 0.2.25 canonical runtime authority validated (2026-09-05)

### Commits / release
- Functional commit: `a1a552c` — Make canonical runtime authoritative for progress
- Release commit: `d6c3c81` — Release Apollo Media Server 0.2.25
- Production Home Assistant Supervisor add-on updated to AMS `0.2.25`.
- Full AMS test suite passed in a disposable Python 3.12 container: `18 passed`.
- Behavioral regression specifically reproduces the historical `42` poisoned-duration failure and verifies that canonical runtime still rejects implausible provider durations.

### Root cause fixed
AMS previously allowed an existing profile `Progress.duration_seconds` to become fallback runtime authority when `Media.runtime_seconds` was absent. A poisoned progress row could therefore become self-locking: legitimate later Kodi playback with the correct duration was rejected because it differed too much from the already-poisoned profile duration.

AMS 0.2.25 separates these responsibilities:
- `Media.runtime_seconds` is canonical media metadata and the only AMS runtime authority used for provider-duration validation.
- `Progress.duration_seconds` is profile viewing state and must never become canonical metadata authority.
- TMDB movie and episode detail enrichment now persists trusted runtime into `Media.runtime_seconds`.
- Continue Watching exposes canonical `expected_duration_seconds` separately from the actual playback `duration_seconds`.

### Production metadata backfill
After deploying 0.2.25:
`POST /metadata/sync`
returned:
`{"status":"ok","received":7845,"enriched":7809,"skipped":0,"failed":36}`

For `42`:
- media UUID: `1e32b039-d78e-498f-9397-14d370f4ab3b`
- IMDb: `tt0453562`
- TMDB: `109410`
- canonical TMDB runtime after sync: `128` minutes
- `expected_duration_seconds`: `7680`
- Kodi canonical UI then displayed the real title duration around `2:08:16`, rather than the poisoned ~18-minute duration.

### Production playback validation
Historical poisoned profile state for `42` before the final test:
- position: `957.208`
- duration: `1086.185`
- updated_at: `2026-09-01T00:32:50`

User played `42` normally and stopped at approximately 25 minutes.

AMS then reported:
- position: `1498.939`
- actual Kodi duration: `7695.691`
- canonical expected duration: `7680`
- progress fraction: `0.19477640149533032`
- updated_at: `2026-09-05T05:26:17`

This proves AMS accepted legitimate Kodi playback and naturally replaced the poisoned profile duration without manual database repair.

### Architecture validated
The production result validates the intended synchronization model:

**Trusted provider/TMDB metadata -> canonical `Media.runtime_seconds` -> validation authority**

**Kodi actual player -> validated playback observation -> `Progress.position_seconds` / `Progress.duration_seconds` -> profile viewing state**

Kodi remains responsible for knowing/reporting actual playback. AMS remains authoritative for canonical profile state and trusted canonical metadata without blindly forcing Kodi state or allowing historical profile progress to impersonate metadata.

### Next work
Return to the Kodi canonical ListItem/resume synchronization work. The unreleased normal-click Kodi experiment remains intentionally dirty and separate:
- `kodi/plugin.video.apollomedia/main.py`
- `kodi/plugin.video.apollomedia/tests/test_resume_retry_intent.py`

There is still no Kodi 0.10.54 release. Kodi 0.10.47 remains the last stable Kodi release.

## Runtime checkpoint — AMS 0.2.26 Next Up validated (2026-09-05)

### Current repository / runtime state
- Branch: `main`
- Current checkpoint HEAD before this handoff update: `564a769`
- Commit: `564a769` — Add AMS Next Up support
- Kodi stable/runtime baseline remains `0.10.56`.
- AMS production runtime is `0.2.26`.
- Home Assistant Supervisor add-on was updated from GitHub after the 0.2.26 commit was pushed.
- Direct AMS API base: `http://hass.pve.home:8099`
- `GET /health` returned:
  `{"status":"ok","service":"apollo-media-server","version":"0.2.26"}`

### Pre-deployment test gate
The exact AMS 0.2.26 release source passed the full disposable-container test suite:

`30 passed`

This includes real SQLAlchemy behavior tests for:
- same-season next-episode advancement
- cross-season advancement
- skipping already watched successors
- preserving target partial progress
- Continue Watching precedence
- future-episode exclusion

### Next Up ownership
Next Up is AMS/profile-owned.

AMS determines the canonical next episode using:
- canonical Apollo media identity
- profile-specific watched/progress state
- TMDB-backed episode ordering/materialization

Kodi and the Home Assistant card are consumers of that same AMS result.

Persistent Continue Watching and Next Up remain separate AMS concepts:
- unfinished episode -> Continue Watching owns the show
- completed/watched episode -> Next Up may advance the show
- future combined profile presentation may place both concepts in one row
- the same show must not appear simultaneously as both in-progress and next-up

### New AMS 0.2.26 endpoints
- `GET /profiles/{profile_id}/next-up`
- `GET /profiles/{profile_id}/media/{media_id}/next-episode`

### Production runtime validation

#### Persistent profile Next Up
Production `GET /profiles/{profile_id}/next-up` returned:

American Dad! — S01E02 — `Threat Levels`

Key state:
- media UUID: `63bc3555-eb68-44da-84d9-98eada69b277`
- canonical ID: `tmdb:1433:s1e2`
- season/episode: `1x02`
- runtime: `22` minutes
- expected duration: `1320` seconds
- position: `0`
- watched: `false`
- state: `next_up`

The preceding American Dad! S01E01 profile record was confirmed as:
- canonical ID: `tmdb:1433:s1e1`
- position: `1288.251`
- duration: `1304.192`
- watched: `true`

Therefore American Dad! was correctly absent from Continue Watching and correctly advanced to S01E02 in Next Up.

#### Direct next-episode resolver
Using American Dad! S01E02 as the source, production:

`GET /profiles/{profile_id}/media/63bc3555-eb68-44da-84d9-98eada69b277/next-episode`

correctly returned:

American Dad! — S01E03 — `Stan Knows Best`

Key state:
- media UUID: `0ccfae0e-531c-45d2-bd0c-4ee10b1d0d01`
- canonical ID: `tmdb:1433:s1e3`
- runtime: `22` minutes
- expected duration: `1320` seconds
- position: `0`
- watched: `false`

#### Cross-season transition
A production direct-successor test using the Reacher season 1 finale correctly crossed the season boundary and returned:

Reacher — S02E01 — `ATM`

Key state:
- media UUID: `b5b707b7-c404-4212-b82b-e1a543a0da3d`
- canonical ID: `tmdb:108978:s2e1`
- runtime: `56` minutes
- expected duration: `3360` seconds
- position: `0`
- watched: `false`

This confirms production Next Up does not stop at season boundaries.

### Continue Watching observations
Production Continue Watching correctly excluded American Dad! because S01E01 is watched.

The existing production database also exposes historical canonicalization/data debt that is not part of the 0.2.26 Next Up regression scope:
- Ted Lasso can appear more than once in raw Continue Watching because multiple unfinished episodes from the same series exist.
- Fight Club exists under both IMDb-style and TMDB-style canonical identities.
- One historical Shameless row contains malformed canonical ID:
  `Player.Property(ApolloCanonicalId)`
- Several older episode rows use legacy show/IMDb-style canonical identities rather than the newer `tmdb:{series}:s{season}e{episode}` form.

Do not migrate or repair these historical rows as part of the 0.2.26 Next Up release unless they are proven to break current behavior.

For future combined Continue Watching + Next Up presentation:
- collapse to one item per show
- unfinished/in-progress episode wins
- otherwise use canonical Next Up
- never show both states for the same show

### Runtime gate result
AMS 0.2.26 Next Up is runtime validated.

Validated production behavior:
- health/version
- persistent profile Next Up
- watched-to-next-unwatched advancement
- Continue Watching precedence
- direct successor resolution
- cross-season transition
- canonical metadata/runtime materialization
- production database compatibility

### Next work
Core Apollo profile/viewing functionality sequence is now:

1. Next Up — COMPLETE and runtime validated in AMS 0.2.26
2. AMS-owned Watchlist — NEXT
3. discovery/list-provider support
4. substantial Home Assistant card work

Trakt is no longer part of the architecture.

AMS owns:
- watchlists
- personalized viewing state
- Continue Watching
- Next Up
- future profile-scoped collections

External providers may supply discovery/catalog/list data, but they do not own Apollo profile state.

### Exact next action
Begin AMS-owned Watchlist design and implementation from this checkpoint.

---

# Apollo AVA / Android TV IME checkpoint — 2026-09-14 05:35:10 UTC

## Purpose of this checkpoint

This section records the Android TV Remote v2 keyboard/IME work completed during the current Apollo AVA session so a future ChatGPT session can resume without reconstructing the protocol investigation.

The current work is on branch `feature/apollo-integrations`. Production AMS on port 8099 and the separate production-migration validation process on port 18101 were intentionally left untouched. Android TV runtime testing is being performed only against the temporary AMS instance on port 18100.

The source tree used by the 18100 test runtime is the repository itself:

```text
/home/apollo/apollo-media-home-assistant/apollo_media_server
```

There is no separate runtime source copy to synchronize.

## Current product sequencing rule

The current Apollo implementation workflow remains:

```text
prove backend behavior
→ add it to the Apollo AVA app
→ prove the app path
→ move to the next capability
```

Do not continue adding unrelated backend capabilities while a proven feature is still waiting to be integrated into the app.

The immediate feature being worked is native Android TV text entry from the AVA remote. Bottom-screen/Dynke configuration, app search, Force Close backend, and voice are intentionally deferred.

## User-required keyboard behavior

The user does not want a workaround based on dismissing the TV keyboard with BACK.

Desired behavior matches the official Google TV phone remote:

```text
TV text field gains focus
→ TV on-screen keyboard remains visible
→ Apollo AVA automatically opens its own native Android keyboard
→ AVA typing is sent through the existing per-device Android TV Remote v2 session
→ text, backspace, Enter, and cursor movement affect the focused TV field in real time
```

Apollo-local search/input remains local to Apollo. Only a text field focused on the controlled TV should activate remote keyboard behavior.

## Previously proven AVA-side behavior

Apollo AVA build 1.7.19 already proved automatic native-keyboard opening:

```text
TV text field focused
→ AMS reports text_input.active=true
→ AVA sees the active state
→ AVA opens native Gboard automatically
```

The AVA secure setting currently required for the software keyboard to remain available is:

```text
show_ime_with_hard_keyboard=1
```

AVA 1.7.19 does not yet forward typed text to AMS. That was intentionally deferred until the correct Remote v2 edit protocol was proven.

## Android TV Remote v2 capability state

Bedroom Google TV Streamer:

```text
device UUID:
bcbeb2e3-c26b-4b4e-b54f-ed1bbdcc65ab

host:
10.10.10.85

MAC:
B8:7B:D4:F1:F3:88

Remote v2 port:
6466
```

The TV advertises Remote v2 capabilities including both IME and VOICE:

```text
Feature.PING
Feature.KEY
Feature.IME
Feature.VOICE
Feature.POWER
Feature.VOLUME
Feature.APP_LINK
```

The TV remote service is:

```text
package: com.google.android.tv.remote.service
version: 7.00.956317615
```

## Text-field detection — proven

When the Google TV field "Search for apps and games" is focused, the TV sends:

```text
remote_ime_key_inject {
  app_info {
    counter: ...
    label: "Search for apps and games"
    app_package: "com.google.android.apps.tv.launcherx"
  }
  text_field_status {
    counter_field: ...
    label: "Search for apps and games"
  }
}

remote_ime_batch_edit {
  ime_counter: 1
  field_counter: 1
}
```

The installed Python `androidtvremote2` library preserves only a small subset of this state. Apollo locally wrapped the live protocol object's `_handle_message` method so AMS can preserve the missing IME data in `DeviceConnection.text_input`.

Current exposed state includes:

```text
active
label
value
start
end
app_counter
counter_field
field_counter
ime_counter
app_package
```

The relevant Pydantic state schema has also been locally expanded with:

```python
text_input: dict | None = None
```

These IME source changes are intentionally still uncommitted while runtime behavior is being proven.

## androidtvremote2 debug logging

The normal AMS configuration exposes `APOLLO_LOG_LEVEL`, but AMS does not apply it to the `androidtvremote2` Python logger. A temporary 18100-only debug launcher was created at:

```text
/tmp/apollo-18100-debug.py
```

It calls `logging.basicConfig(level=logging.DEBUG)` and explicitly sets:

```python
logging.getLogger("androidtvremote2").setLevel(logging.DEBUG)
```

18100 must be started with the repo source directory on `PYTHONPATH` because the launcher itself lives in `/tmp`:

```text
PYTHONPATH=/home/apollo/apollo-media-home-assistant/apollo_media_server
```

This successfully exposed full incoming Remote v2 protobuf messages in:

```text
~/apollo-androidtv-test-runtime/ams-18100.log
```

## Critical protocol discovery: androidtvremote2 uses the wrong IME synchronization counters

The Python library's normal `send_text()` creates `RemoteImeBatchEdit` using its own:

```text
ime_counter
field_counter
```

Those values remain 1/1 in the tested session and are not the values Google TV validates when its on-screen keyboard is active.

Reverse engineering of the Google TV Remote Service APK showed that incoming batch edits are rejected unless two generation/state counters match the TV's current input field.

The TV emits clear rejection logs:

```text
Ignoring edit, the input field has changed from <sent> to <expected>
Ignoring edit, the input field content has changed from <sent> to <expected>
```

### First synchronization counter — proven

A normal library packet used first counter 1 while the TV expected values such as 47/49.

Apollo preserved `remote_ime_key_inject.app_info.counter` separately as:

```text
app_counter
```

Fresh debug capture later showed:

```text
app_info.counter: 51
text_field_status.counter_field: 291
remote_ime_batch_edit.ime_counter: 1
remote_ime_batch_edit.field_counter: 1
```

When a temporary proof packet sent:

```text
RemoteImeBatchEdit.ime_counter = app_counter
```

the TV passed the first validation gate and moved to the second rejection:

```text
Ignoring edit, the input field content has changed from 1 to 291
```

Therefore:

```text
RemoteImeBatchEdit.ime_counter
    = remote_ime_key_inject.app_info.counter
```

is proven.

### Second synchronization counter — proven

The expected second value in the rejection above was exactly:

```text
remote_ime_key_inject.text_field_status.counter_field = 291
```

Apollo therefore changed the temporary proof packet to:

```text
RemoteImeBatchEdit.field_counter
    = text_field_status.counter_field
```

A later live field state was:

```json
{
  "active": true,
  "label": "Search for apps and games",
  "value": "",
  "start": 0,
  "end": 0,
  "app_counter": 55,
  "counter_field": 307,
  "field_counter": 1,
  "ime_counter": 1,
  "app_package": "com.google.android.apps.tv.launcherx"
}
```

With both synchronized values sent:

```text
RemoteImeBatchEdit.ime_counter   = 55
RemoteImeBatchEdit.field_counter = 307
```

the text:

```text
APOLLO
```

appeared immediately in the focused Google TV field **while the TV's own on-screen keyboard remained visible**.

This is the key runtime proof.

## Proven counter mapping

The correct Remote v2 mapping for the tested Google TV implementation is:

```text
RemoteImeBatchEdit.ime_counter
    = remote_ime_key_inject.app_info.counter

RemoteImeBatchEdit.field_counter
    = remote_ime_key_inject.text_field_status.counter_field
```

The `androidtvremote2` library's exposed batch-edit counters (`ime_counter=1`, `field_counter=1`) are not sufficient for synchronized edits while the TV virtual keyboard is active.

## Current temporary proof implementation

The current local source still contains temporary proof-only commands in the Android TV key-command allowlist, including items used during investigation such as:

```text
KEYCODE_A
KEYCODE_DEL
KEYCODE_ENTER
TEXT:APOLLO
TEXT:X
TEXTFIX:APOLLO
```

These are not final API design and must be removed before the backend work is considered complete.

The temporary `TEXTFIX:APOLLO` path currently constructs a `RemoteMessage` directly and sends a `remote_ime_batch_edit` through:

```python
protocol = connection.remote._remote_message_protocol
protocol._send_message(msg)
```

Its synchronized counters now use:

```python
batch.ime_counter = int(connection.text_input["app_counter"])
batch.field_counter = int(connection.text_input["counter_field"])
```

The edit body currently mirrors the library's basic insertion structure and was sufficient to prove that synchronized text entry works.

## Important test nuance

A Remote v2 connection restart clears Apollo's in-memory text-field state until the TV emits a fresh IME/key-inject event.

Therefore, after restarting 18100, do **not** immediately send a synchronized edit if `/state` shows:

```text
active: false
app_counter: 0
counter_field: 0
```

Refocus the TV text field first and verify a fresh state such as:

```text
active: true
app_counter: <nonzero live value>
counter_field: <nonzero live value>
```

Only then is a synchronized edit test valid.

One intermediate test produced only a lone `O` after a restart with zeroed state. That result is not part of the final protocol proof.

## Other keyboard operations already proven

Before the synchronized-counter discovery, these Remote v2 operations were separately proven while the TV field remained focused but the TV keyboard had been manually hidden:

```text
text insertion
KEYCODE_DEL       → Backspace
KEYCODE_ENTER     → Enter
DPAD_LEFT/RIGHT   → cursor movement
text insertion at current cursor
```

Those tests established that the overall Remote v2 control session and key semantics work.

The new synchronized-counter discovery removes the need to hide the TV keyboard for text insertion.

## Official Google remote comparison

The official Google TV phone remote was tested against the same Bedroom Google TV Streamer.

Observed behavior:

```text
TV keyboard remains visible
phone keyboard opens
phone can type into the TV field live
```

TV logs showed the official phone and Apollo both open the same:

```text
virtual-remote
```

input bridge.

The separate `virtual-remote-2` path was investigated and ruled out as the missing mechanism.

The missing behavior was the synchronized IME edit protocol/state, specifically the correct generation counters documented above.

## Current local files/backups to clean before final commit

During investigation, local backup files were created, including:

```text
apollo_media_server/app/services/android_tv_control.py.before-counter-field
apollo_media_server/app/services/android_tv_control.py.before-ime-counter-proof
apollo_media_server/app/services/android_tv_control.py.before-app-counter
```

These should remain untracked and should be removed before the final implementation commit.

The temporary debug launcher:

```text
/tmp/apollo-18100-debug.py
```

is also test-only and not part of the repository.

## Exact next implementation step

Do **not** wire AVA typing directly into the temporary `TEXTFIX:APOLLO` command.

The next task is to replace the proof path with a proper backend text-input primitive.

Recommended API separation:

```text
POST /devices/{device_id}/text
{"text":"..."}
```

or an equivalent dedicated IME/edit endpoint.

The implementation should:

1. remove `TEXTFIX:APOLLO` from the key-command path;
2. remove other temporary text proof commands from the permanent key allowlist;
3. keep normal Android TV key commands in `send_key()`;
4. add a dedicated text/IME service function;
5. require a live active text-input state;
6. build `RemoteImeBatchEdit` using:
   ```text
   ime_counter   = connection.text_input["app_counter"]
   field_counter = connection.text_input["counter_field"]
   ```
7. send the edit through the existing persistent per-device Remote v2 protocol;
8. expose the operation through a clean AMS device endpoint;
9. prove that endpoint manually while the TV keyboard remains visible;
10. only after that proof, wire AVA's native Android keyboard edits into the endpoint.

The first inspection planned for that work is to locate the current command route/request schema and then implement the dedicated text endpoint cleanly.

## Release/commit state

This handoff update intentionally does **not** commit the current Android TV IME source changes.

The IME work remains an active runtime experiment until the temporary proof path is replaced with the proper API and tested.

This checkpoint commit should contain only `PROJECT_HANDOFF.md`.

Repository HEAD before this handoff commit:

```text
6bc85508f1deeda4dfd9786a8973c5bac9d1335f
```

Branch:

```text
feature/apollo-integrations
```

