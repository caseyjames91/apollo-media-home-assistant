# Apollo IR / RF Architecture

## Purpose

Apollo IR turns compatible handheld remotes, starting with the AVA Home Remote,
into room-local Home Assistant infrared emitters while keeping learning and
command ownership centralized in Home Assistant.

## Ownership

- **BroadLink RM4 Pro**: learning hardware for IR and RF.
- **Home Assistant / Apollo IR**: command library, learning orchestration,
  status, room routing, and device ownership.
- **AVA IR Bridge app**: user-facing learning/control UI plus room-local IR
  transmission through Android `ConsumerIrManager`.
- **Apollo Media card / activities**: consumer of the room-control layer.

The AVA app must not scrape Home Assistant `.storage` files and must not store
device-specific IR libraries as APK constants.

## Confirmed hardware state

AVA Home Remote model RX1:
- Android 11 / API 30.
- `android.hardware.consumerir` is exposed.
- Android `consumer_ir` Binder service is present.
- Native `ConsumerIrManager` transmission has been proven against an LG
  soundbar.
- LAN HTTP -> AVA IR Bridge -> ConsumerIrManager -> IR target is proven.
- A BroadLink-learned IR packet has been successfully decoded and replayed by
  the AVA.

## Target Home Assistant model

Apollo IR should integrate with Home Assistant's native `infrared` platform.
The AVA should appear as an `InfraredEmitterEntity`, allowing other HA
integrations to use it as a protocol-agnostic IR emitter.

The AVA transport API should therefore gain a raw endpoint:

`POST /ir/raw`

Payload concept:

```json
{
  "modulation_hz": 38000,
  "timings_us": [9000, -4500, 560, -560]
}
```

Home Assistant owns protocol encoding. AVA only transmits the requested raw
timings.

## Learning UX

The AVA app is the preferred UI.

### IR

1. User taps Learn IR on AVA.
2. User chooses/creates device and command names.
3. AVA requests a learning job from Apollo IR in HA.
4. HA starts the configured BroadLink learner.
5. AVA shows: `Press the Power button`.
6. HA reports completion or timeout.
7. AVA shows `Learned`.
8. User can test using the selected room emitter.

### RF

1. User taps Learn RF.
2. HA starts BroadLink RF sweep.
3. AVA shows `Hold Power — searching for frequency`.
4. HA reports frequency found.
5. AVA shows `Press Power again`.
6. HA captures the packet and reports success.
7. AVA shows `Learned`.

RF remains a Home Assistant/BroadLink transmit path unless a future Apollo
remote gains compatible RF transmit hardware.

## Development checkpoints

### 0.1 Repo bootstrap
- Import AVA IR Bridge source into monorepo.
- Add Apollo IR custom-component skeleton.
- Document ownership and API contract.

### 0.2 Native AVA emitter
- Add `/ir/raw` to Android bridge.
- Implement `InfraredEmitterEntity.async_send_command`.
- Verify an HA native IR command reaches AVA and controls a target.

### 0.3 Learning jobs
- Add authenticated HA API for create/status/cancel learning jobs.
- Mirror IR and RF learning phases to AVA.
- Do not make the AVA depend on HA frontend notifications.

### 0.4 Command library
- Friendly device/command management.
- Test/delete/rename.
- Room emitter selection.
- Migration/import path for already-learned BroadLink commands.

### 0.5 AVA learning UI
- HA server/token setup.
- Learner selection.
- IR/RF learn buttons.
- Live phase/status feedback.
- Device/command browser and test actions.

## Security

- Local-only transport.
- HA authentication is required for AVA -> HA management calls.
- BroadLink can be blocked from WAN after the local flow is validated.
- APK signing keys are not committed to Git.
