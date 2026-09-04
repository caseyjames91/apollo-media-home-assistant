# Apollo Media Project Handoff

Last updated: 2026-09-04
Status: Stable checkpoint

## Purpose

`PROJECT_HANDOFF.md` is the durable source for restoring Apollo project context when a ChatGPT conversation reaches its limit.

A new session should be able to read this file, inspect Git since its checkpoint, and safely continue without reconstructing the project from old chats.

This is a LIVE CHECKPOINT, not a one-time project summary.

## Source of truth

Repository: `caseyjames91/apollo-media-home-assistant`

Branch: `main`

Checkpoint commit:

`adb4f499f9670f8b1209815cb220a846575ef40c`

Checkpoint history:

- `adb4f49` — Mark Apollo Media 0.10.46 stable
- `52f4a74` — Release Apollo Media 0.10.46
- `5ace03d` — Preserve Kodi native resume choice for remote playback

Stable release: `0.10.46`

Runtime-tested Kodi version: `0.10.46`

A new session must verify repository HEAD against this checkpoint before continuing. If HEAD has moved, inspect commits after the checkpoint before taking action.

## Current state

Apollo Media 0.10.46 is released, installed in Kodi through the normal Apollo repository/update workflow, runtime-tested, and marked stable.

The latest functional change originated in:

`5ace03d — Preserve Kodi native resume choice for remote playback`

### Resume regression root cause

Apollo `_resolve_remote()` was injecting Apollo/AMS stored resume data into the resolved Kodi ListItem using:

- `ams.resume(...)`
- `tag.setResumePoint(...)`

This interfered with Kodi's native Resume / Start from beginning behavior for remote playback.

### Fix

Removed Apollo resume injection from `_resolve_remote()` so Kodi owns its native resume-choice behavior.

### Runtime validation completed for 0.10.46

Verified:

- runtime `addon.xml` reported `0.10.46`
- runtime `_resolve_remote()` contained no `ams.resume(...)`
- runtime `_resolve_remote()` contained no `tag.setResumePoint(...)`
- remote/debrid playback with existing saved progress was tested
- Resume worked
- Start from beginning worked

After runtime approval, 0.10.46 was promoted stable using:

`./scripts/apollo mark-stable 0.10.46`

## Established release and deployment workflow

Do NOT manually copy development addon files into Kodi as the normal workflow.

The established workflow is:

1. Make and test source changes in the repository.
2. Commit and push the functional change.
3. Run release preflight:

   `./scripts/release-apollo-client.sh --check X.Y.Z`

4. Create the numbered release:

   `./scripts/release-apollo-client.sh X.Y.Z`

5. Refresh/check the Apollo Kodi repository and install/update the numbered version in Kodi.
6. Verify the actual installed runtime version and relevant runtime source.
7. Perform the targeted runtime regression test.
8. Only after runtime approval:

   `./scripts/apollo mark-stable X.Y.Z`

9. If runtime validation fails, do not mark the release stable. Use the rollback framework.

Do not invent `docker cp`, `scp`, `rsync`, or other manual deployment methods unless the project intentionally changes its deployment workflow.

A numbered release is NOT automatically stable. Runtime validation and explicit stable promotion are separate gates.

## Architecture rules

### Core ownership rule

**Rooms own playback devices; profiles own viewing state.**

Room configuration owns:

- Kodi target
- TV/playback target
- device-specific capabilities
- launch actions
- room-specific playback behavior

Profile state owns:

- watched history
- resume position
- Continue Watching
- lists
- user-specific viewing state

This ownership rule guides:

- playback handoff
- profile switching
- Continue Watching
- multi-room behavior
- future session transfer features

### UI and playback ownership

The Home Assistant Apollo card is intended to be the primary phone/tablet browse and control UI.

Browsing on the card should not alter Kodi's visible TV UI.

“Show on TV” is the explicit browse-context handoff.

When diagnosing regressions, inspect the complete ownership chain:

Kodi addon -> Home Assistant/package -> card/UI

Do not assume something is a card bug merely because the symptom appears on the card.

## Working conventions

- Prefer root-cause fixes rather than workaround or compatibility patches.
- During interactive terminal diagnosis, use one command at a time and inspect its output before proceeding.
- Do not invent deployment methods.
- Preserve the normal Git -> release -> Kodi repository update -> runtime test -> stable promotion workflow.
- A numbered release is not stable until runtime-tested and explicitly promoted.
- Full standard versioned release bundles remain expected.
- For releases, identify:
  - files with functional changes
  - files with version-only changes
  - unchanged files included in the bundle

## Handoff maintenance protocol

`PROJECT_HANDOFF.md` is a live project checkpoint, not a one-time summary.

Update this file whenever a meaningful project state transition occurs, including:

- a functional code change is committed
- a numbered release is created
- Kodi/runtime deployment changes
- a runtime test passes or fails
- a root cause is established
- an architecture or ownership decision is made
- a release is marked stable
- a rollback occurs
- the exact next task, test, or command changes
- a major TODO is added, completed, or materially redefined

Do not wait until the conversation is nearly full.

Update the handoff immediately after a meaningful state transition so an unexpected conversation cutoff does not lose the reasoning or continuation point.

### Required fields to keep current

Every meaningful handoff update should verify and refresh, as applicable:

- current branch
- current Git HEAD / checkpoint SHA
- latest released version
- version actually installed in runtime
- current stable version
- what changed
- why it changed
- whether the change has reached runtime
- tests already performed and their results
- known-good observations
- known-bad observations / unresolved issues
- exact next action, test, or command
- release/stable gating status
- relevant workflow or architecture decisions

If a coding task directly changes GitHub, updating `PROJECT_HANDOFF.md` should be part of the same work session whenever that change materially changes project state. It should not be treated as optional cleanup.

## New-chat recovery procedure

At the start of a new Apollo chat:

1. Read `PROJECT_HANDOFF.md`.
2. Read the current repository `main` HEAD.
3. Compare HEAD with the checkpoint commit recorded here.
4. If HEAD is newer, inspect commits since the checkpoint before proceeding.
5. Verify release/runtime versions if the next task depends on deployed behavior.
6. Continue from the recorded continuation point rather than reconstructing the project from chat history.
7. Update this file again after the next meaningful state transition.

The desired user experience is that a new project conversation can simply be told:

**“Resume Apollo.”**

and recover the project safely.

## Source-of-truth priority

When information conflicts, use this order:

1. Actual runtime behavior/state
2. Current Git repository contents and history
3. `PROJECT_HANDOFF.md`
4. Old chat summaries or memory

If this file disagrees with Git or runtime evidence, treat the handoff as stale and update it before continuing.

## Current continuation point

Apollo Media 0.10.46 is a clean stable checkpoint.

The remote playback Resume / Start from beginning regression is closed.

Do not invent an unfinished implementation as the next task. The next development task should be explicitly chosen from the roadmap or current user request.

## Known future roadmap

### Ensure Kodi Ready lifecycle

If Kodi is not running:

- use a device-specific launch action
- wait until the associated Home Assistant Kodi `media_player` becomes available/ready
- then continue the original playback request

This lifecycle should apply consistently to:

- Play
- Resume
- Play Locally
- remote-stream playback

The UI should expose a visible “Starting...” state while Kodi is becoming ready.

### Apollo Companion

A lightweight Android companion service/app that:

- exposes current Kodi playback as a native Android MediaSession
- provides lock-screen/system media controls
- relays play/pause/next/previous controls back through Home Assistant/Kodi

The Home Assistant Apollo card remains the primary UI. The companion is an OS-integration layer, not a replacement UI.

### Playback handoff / Recent Sessions

Support remote-to-remote playback handoff.

A room's Apollo remote/card should be able to show unfinished sessions from other rooms/devices and offer:

“Resume here”

Session state should retain enough information to identify:

- media/title
- resume position
- originating room/device
- recency
- source/resolution hints when useful

The receiving room resolves the best playback source available to it.

### YouTube integration

Bring YouTube into the same Apollo experience for:

- browsing
- playback
- profile-aware recommendations
- handoff to Kodi/TV
- minimal or no TV-side interaction

## Stable checkpoint summary

Stable version: `0.10.46`

Runtime-tested version: `0.10.46`

Current checkpoint:

`adb4f499f9670f8b1209815cb220a846575ef40c`

Latest functional fix:

`5ace03d — Preserve Kodi native resume choice for remote playback`

Latest release commit:

`52f4a74 — Release Apollo Media 0.10.46`

Latest stable-promotion commit:

`adb4f49 — Mark Apollo Media 0.10.46 stable`
