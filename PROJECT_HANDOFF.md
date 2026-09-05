# CURRENT AUTHORITATIVE CHECKPOINT — 2026-09-05

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
