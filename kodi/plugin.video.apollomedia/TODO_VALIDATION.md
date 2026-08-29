# Apollo Media 0.9 Validation TODO

Status values: `NOT TESTED`, `PASS`, `FAIL`

## Phase 1 — Core navigation

- [x] `PASS` Root menu opens and all expected entries are present.
- [x] `PASS` Library Movies opens.
- [ ] `NOT TESTED` Library Shows opens quickly and reflects corrected Jellyfin metadata directly.
- [x] `PASS` Popular Movies opens.
- [x] `PASS` Popular Shows opens and identifies local shows.
- [ ] `NOT TESTED` Trending Movies opens.
- [ ] `NOT TESTED` Trending Shows opens.
- [ ] `NOT TESTED` Search Movies works.
- [ ] `NOT TESTED` Search Shows works.
- [ ] `NOT TESTED` Show → Seasons navigation works.
- [ ] `NOT TESTED` Season → Episodes navigation works.

## Phase 2 — Metadata and identity

- [ ] `NOT TESTED` Numeric/digit-leading show titles display correctly.
- [ ] `NOT TESTED` Library show sorting uses corrected/canonical title.
- [ ] `NOT TESTED` Movie metadata displays correctly.
- [ ] `NOT TESTED` Show metadata displays correctly.
- [ ] `NOT TESTED` Season artwork uses season art when available, otherwise show art.
- [ ] `NOT TESTED` Episode artwork uses episode art/still when available, otherwise show art.
- [ ] `NOT TESTED` Continue Watching episodes use show artwork.
- [x] `PASS` Discovery movies/shows/seasons/episodes show the subtle local dot when present in Jellyfin.
- [ ] `NOT TESTED` Local and discovery versions resolve to the same canonical identity.

## Phase 3 — Continue Watching

- [ ] `NOT TESTED` card playing → stopped optimistic reconciliation preserves the exact internal, outer, window, rail, and modal scroll positions without an intermediate zero assignment.
- [ ] `NOT TESTED` delayed authoritative CW reorder/removal after stop replaces only the CW rail, preserves modal/view state, and retains Apollo order.
- [ ] `NOT TESTED` card stable CW identity/order with changed progress patches poster progress without calling full `render()`.
- [ ] `NOT TESTED` repeated in-playback CW progress updates cause no full-card render or visible flash.
- [ ] `NOT TESTED` progress-only reconciliation preserves card/page vertical scroll and CW horizontal rail scroll.
- [ ] `NOT TESTED` an open CW detail modal remains open and updates its watched/remaining progress in place.
- [ ] `NOT TESTED` authoritative CW membership/order changes still replace the row order while preserving active view, modal, and scroll state.
- [ ] `NOT TESTED` 0.9.48 opening or closing a card Continue Watching detail performs no Kodi action.
- [ ] `NOT TESTED` 0.9.48 local and remote Continue Watching stop events retain the 0.9.46 single-poller targeted reconciliation behavior.
- [ ] `NOT TESTED` 0.9.46 active-player polling skips an overlapping Continue Watching reconciliation instead of queuing an immediate duplicate.
- [ ] `NOT TESTED` 0.9.46 changing the configured Kodi player triggers exactly one targeted refresh; ordinary HA and same-target config updates trigger none.
- [ ] `NOT TESTED` 0.9.45 compare `APOLLO_CW_DEBUG GUI AFTER_SORT_ORDER` with `HEADLESS AFTER_SORT_ORDER` for the same activity snapshot.
- [ ] `NOT TESTED` 0.9.45 compare each route's `FINAL_ENTRY` order with its `ADD_DIRECTORY_ITEM` dispatch order.
- [ ] `NOT TESTED` 0.9.45 confirm each `CONSUMER_BEGIN` reports exactly one timeline build through `entries_call_count=1`.
- [ ] `NOT TESTED` 0.9.44 rendering a local item preserves Jellyfin `LastPlayedDate` instead of fabricating current activity.
- [ ] `NOT TESTED` 0.9.44 missing Jellyfin `LastPlayedDate` preserves existing Apollo activity or uses a neutral timestamp.
- [ ] `NOT TESTED` 0.9.44 Kodi GUI and headless Continue Watching routes retain the same Apollo insertion order before and after rendering.
- [ ] `NOT TESTED` 0.9.44 Kodi displays Continue Watching as unsorted and does not reorder Apollo's timeline.
- [ ] `NOT TESTED` 0.9.42 local Apollo/Kodi playback moves a Jellyfin-backed item using newer Apollo `progress.updated` activity.
- [ ] `NOT TESTED` 0.9.42 external Jellyfin playback moves an item using newer `UserData.LastPlayedDate` activity.
- [ ] `NOT TESTED` 0.9.42 merging both activity timestamps does not duplicate a local identity.
- [ ] `NOT TESTED` 0.9.41 Jellyfin and Apollo-only entries form one newest-first activity timeline.
- [ ] `NOT TESTED` 0.9.41 items without usable activity timestamps sort after timestamped items.
- [ ] `NOT TESTED` 0.9.41 a shared Jellyfin/Apollo identity still renders once with canonical Jellyfin progress.
- [ ] `NOT TESTED` Local Jellyfin movie resume appears once.
- [ ] `NOT TESTED` Local Jellyfin episode resume appears once.
- [ ] `NOT TESTED` Apollo remote-progress movie appears once.
- [ ] `NOT TESTED` Apollo remote-progress episode appears once.
- [ ] `NOT TESTED` Jellyfin + Apollo duplicate identity is deduplicated.
- [ ] `NOT TESTED` Resume positions are correct.
- [ ] `NOT TESTED` Trakt integration added later without changing the normalized identity model.

## Phase 4 — Local playback

- [ ] `NOT TESTED` 0.9.49 card local movie Start Over resolves with `StartOffset=0`, omits positive resume metadata, and begins at zero.
- [ ] `NOT TESTED` 0.9.49 card local episode Start Over behaves identically.
- [ ] `NOT TESTED` 0.9.49 confirmed card local Resume still starts at saved position without a Kodi dialog.
- [ ] `NOT TESTED` 0.9.49 Start Over does not delete or reset authoritative saved progress before playback reports new state.
- [ ] `NOT TESTED` 0.9.48 card local movie Resume starts at the authoritative saved position without a Kodi dialog.
- [ ] `NOT TESTED` 0.9.48 card local movie Start Over explicitly starts at zero without a Kodi dialog.
- [ ] `NOT TESTED` 0.9.48 card local episode Resume and Start Over match movie behavior.
- [ ] `NOT TESTED` 0.9.48 configured `player_entity` A/B targeting remains correct for both card playback choices.
- [ ] `NOT TESTED` 0.9.47 headless/card local entries use `play_jellyfin_native`, which launches the unchanged `play_jellyfin` route through `PlayMedia`.
- [ ] `NOT TESTED` 0.9.47 card-launched local movies and episodes honor Kodi's configured Ask-if-resumable chooser.
- [ ] `NOT TESTED` 0.9.47 normal Kodi addon local selection remains on the direct `play_jellyfin` directory-item path.
- [ ] `NOT TESTED` 0.9.46 card-launched local Jellyfin playback presents Kodi's native Resume / Start from beginning prompt.
- [ ] `NOT TESTED` 0.9.46 local playback still reports progress and updates Continue Watching after either native prompt choice.
- [ ] `NOT TESTED` Local movie prefers Jellyfin playback.
- [x] `PASS` Local episode prefers Jellyfin playback.
- [ ] `NOT TESTED` Jellyfin playback starts successfully.
- [ ] `NOT TESTED` Jellyfin resume point is honored.
- [ ] `NOT TESTED` Jellyfin playback progress is reported.
- [ ] `NOT TESTED` Jellyfin stop/resume state updates correctly.
- [ ] `NOT TESTED` Jellyfin watched/completed state updates correctly.

## Phase 5 — Remote playback

- [ ] `NOT TESTED` 0.9.52 local active episode restores safe show/season navigation after card reload while Try Next remains hidden.

- [ ] `NOT TESTED` 0.9.51 browser refresh during active remote playback restores safe Apollo identity, Try Next, show navigation, and season navigation without exposing a stream URL.

- [ ] `NOT TESTED` 0.9.50 explicit remote Resume with saved=1800 starts at 1800 and receives no later seek to another value.
- [ ] `NOT TESTED` 0.9.50 explicit remote Start Over with saved=3000 starts at zero and never reapplies 3000.
- [ ] `NOT TESTED` 0.9.50 Start Over preserves saved progress until normal playback reporting advances it.
- [ ] `NOT TESTED` 0.9.50 playback from zero reaching 600 and stopping persists approximately 600 normally.
- [ ] `NOT TESTED` 0.9.50 a later Resume uses only the newest saved position.
- [ ] `NOT TESTED` 0.9.50 Try Next at live position 2500 updates the source session and does not revert to the original resume position.
- [ ] `NOT TESTED` 0.9.50 normal Kodi addon remote Resume / Start Over prompts remain unchanged.
- [ ] `UNRESOLVED` Remote Resume can differ slightly from the card's saved time after startup (observed card 26:28, playback 26:16). 0.9.50 fixed the major double-seek/Start Over behavior; investigate this remaining offset handoff separately in a future addon change.
- [ ] `NOT TESTED` 0.9.48 card remote movie Resume and Start Over are explicit and produce no Kodi-side chooser.
- [ ] `NOT TESTED` 0.9.48 card remote episode Resume and Start Over are explicit and produce no Kodi-side chooser.
- [ ] `NOT TESTED` 0.9.48 normal Kodi addon remote playback retains Apollo's custom resume chooser.
- [ ] `NOT TESTED` 0.9.46 remote playback retains Apollo's custom resume selection and explicit start offset.
- [ ] `NOT TESTED` 0.9.43 Apollo-owned remote resume prompts once and starts with explicit `StartOffset`.
- [ ] `NOT TESTED` 0.9.43 Start from beginning supplies explicit `StartOffset=0` without a Kodi resume prompt.
- [ ] `NOT TESTED` 0.9.43 Try Next carries the current position without exposing a native resume prompt.
- [ ] `NOT TESTED` 0.9.43 every Choose Remote Stream context action launches `choose_external` with `RunPlugin`.
- [ ] `NOT TESTED` 0.9.43 local movie/episode chooser returns to the current directory and starts the selected source without a blank window or crash.
- [ ] `NOT TESTED` 0.9.42 chooser Play launches the dedicated `play_session_stream` route through `PlayMedia`.
- [ ] `NOT TESTED` 0.9.42 chooser selection from local movies/episodes starts playback instead of opening a blank directory.
- [ ] `NOT TESTED` 0.9.42 selected-source playback preserves source-session resume and Jellyfin association.
- [ ] `NOT TESTED` TorBox device linking works.
- [ ] `NOT TESTED` Comet source lookup works.
- [x] `PASS` Torrentio source lookup works.
- [x] `PASS` Debridio source lookup works with a configured addon URL.
- [x] `PASS` Multiple enabled provider toggles merge source results correctly.
- [ ] `NOT TESTED` Source dedupe works.
- [ ] `NOT TESTED` Source ranking works.
- [ ] `NOT TESTED` Best compatible source auto-plays.
- [ ] `NOT TESTED` Manual Choose Remote Source works.
- [ ] `NOT TESTED` Remote resume point is honored.
- [ ] `NOT TESTED` Apollo progress DB updates during remote playback.

## Phase 6 — Stream recovery / learning

- [ ] `NOT TESTED` Try Next Stream works.
- [ ] `NOT TESTED` Try Next Stream preserves playback position.
- [ ] `NOT TESTED` Flag Current Stream opens reason selection.
- [ ] `NOT TESTED` Bad colors/HDR flag works.
- [ ] `NOT TESTED` No audio flag works.
- [ ] `NOT TESTED` Unsupported codec flag works.
- [ ] `NOT TESTED` Buffering flag records.
- [ ] `NOT TESTED` Wrong-content flag records.
- [ ] `NOT TESTED` Flagging can update device compatibility profile.
- [ ] `NOT TESTED` Playback error automatically advances to next stream.
- [ ] `NOT TESTED` Auto-advance preserves playback position.

## Phase 7 — Device compatibility and settings

- [ ] `NOT TESTED` Settings menu opens with all section, group and control labels visible.
- [ ] `NOT TESTED` Comet/Torrentio/Debridio provider toggles persist independently.
- [ ] `NOT TESTED` Resolution settings persist.
- [ ] `NOT TESTED` HDR/Dolby Vision settings persist.
- [ ] `NOT TESTED` Video codec settings persist.
- [ ] `NOT TESTED` Audio format settings persist.
- [ ] `NOT TESTED` Detect Device Compatibility runs.
- [ ] `NOT TESTED` Detected resolution is reasonable.
- [ ] `NOT TESTED` Detected HDR capabilities are reasonable.
- [ ] `NOT TESTED` Detected passthrough/audio capabilities are reasonable.
- [ ] `NOT TESTED` Manual overrides remain editable after detection.

## Phase 8 — Deferred until Kodi is stable

- [ ] `NOT TESTED` Add Trakt authentication.
- [ ] `NOT TESTED` Use Trakt for watched/history authority.
- [ ] `NOT TESTED` Use Trakt for Trending/Popular/list sources where appropriate.
- [ ] `NOT TESTED` Merge Trakt into Continue Watching/history model.
- [ ] `NOT TESTED` Reconnect Home Assistant card to normalized Apollo data.
- [ ] `NOT TESTED` Reimplement Show on TV against stable addon routes.
- [ ] `NOT TESTED` Revisit Favorites/watchlist.
- [ ] `NOT TESTED` Final modal/card styling.

## Current next item

Current item: capture and compare **0.9.45 structured GUI/headless Continue Watching diagnostics**.






- [x] `PASS` Local discovery episode plays through Jellyfin.
- [x] `PASS` Non-local discovery episode uses Apollo remote playback.





- [ ] `NOT TESTED` Continue Watching episodes consistently display `Show Title • S01E01 • Episode Name` for both Jellyfin resume and Apollo remote progress.



- [ ] `NOT TESTED` Remove from Continue Watching context action works for Jellyfin resume items and Apollo remote-progress items.


- [ ] `NOT TESTED` Play from Stream auto-selects a remote source for local movies.
- [ ] `NOT TESTED` Play from Stream auto-selects a remote source for local episodes.
- [ ] `NOT TESTED` Normal click on local items still prefers Jellyfin.


- [ ] `NOT TESTED` Choose Remote Stream opens the manual source list for local movies.
- [ ] `NOT TESTED` Choose Remote Stream opens the manual source list for local episodes.



- [ ] `NOT TESTED` Remote override inherits Jellyfin resume position for local movies.
- [ ] `NOT TESTED` Remote override inherits Jellyfin resume position for local episodes.
- [ ] `NOT TESTED` Choosing a remote override does not clear or alter Jellyfin resume state.


- [ ] `NOT TESTED` Remote override writes updated progress back to Jellyfin.
- [ ] `NOT TESTED` Local remote override does not create a duplicate Apollo Continue Watching entry.
- [ ] `NOT TESTED` Completing a local item through a remote override updates Jellyfin watched state.


- [ ] `NOT TESTED` Unified progress: local Jellyfin playback and local remote override show the same resume position.
- [ ] `NOT TESTED` Unified progress: remote override advances the single Apollo progress record and Jellyfin position together.
- [ ] `NOT TESTED` Unified progress: playback in Jellyfin app imports into Apollo on next item load.
- [ ] `NOT TESTED` Unified progress: stale legacy local Apollo resume does not override current Jellyfin position.





- [x] `PASS` Kodi built-in `Reset resume position` clears the native resume indicator.
- [ ] `NOT TESTED` Clean-zero unified progress test after Kodi native resume reset.


- [ ] `NOT TESTED` 0.9.22 imports a newer Jellyfin-app resume position into Apollo/Kodi.
- [ ] `NOT TESTED` 0.9.22 local playback overrides an older Kodi native bookmark with canonical progress.
- [ ] `NOT TESTED` 0.9.22 Play from Stream overrides an older remote-stream bookmark with canonical progress.


- [ ] `NOT TESTED` 0.9.23 local Kodi playback explicitly updates Jellyfin resume user data.
- [ ] `NOT TESTED` 0.9.23 local remote-stream override explicitly updates Jellyfin resume user data.


- [ ] `NOT TESTED` 0.9.24 Popular Movies local item shows the same resume position as Continue Watching.
- [ ] `NOT TESTED` 0.9.24 Trending/Search local movie rows use canonical resume state.


- [ ] `NOT TESTED` 0.9.25 Play from Stream prompts Resume vs Start from beginning when progress exists.
- [ ] `NOT TESTED` 0.9.25 Resume starts the remote stream at the canonical position.
- [ ] `NOT TESTED` 0.9.25 Start from beginning resets Jellyfin resume and starts remote playback at 0.
- [ ] `NOT TESTED` 0.9.25 remote playback after Start from beginning advances Jellyfin progress from the new position.



- [ ] `NOT TESTED` 0.9.27 non-local movie context menu shows Choose Remote Stream.
- [ ] `NOT TESTED` 0.9.27 non-local episode context menu shows Choose Remote Stream.


- [ ] `NOT TESTED` 0.9.28 every playable movie exposes Choose Remote Stream.
- [ ] `NOT TESTED` 0.9.28 every playable episode exposes Choose Remote Stream.


- [ ] `NOT TESTED` 0.9.29 manual list context menu exposes Play + Flag Stream.
- [ ] `NOT TESTED` 0.9.29 flagged stream shows ⚠ and moves below clean streams.
- [ ] `NOT TESTED` 0.9.29 flagged stream context menu exposes Unflag Stream.
- [ ] `NOT TESTED` 0.9.29 unflag removes ⚠ without starting playback.
- [ ] `NOT TESTED` 0.9.29 Wrong language works from active and manual flag dialogs.


- [ ] `NOT TESTED` 0.9.30 custom StreamChooser dialog opens from Choose Remote Stream.
- [ ] `NOT TESTED` 0.9.30 bundled PNG flag badge renders in Kodi.
- [ ] `NOT TESTED` 0.9.30 Play button starts selected source.
- [ ] `NOT TESTED` 0.9.30 Flag/Unflag button updates selected source and refreshes dialog state.
- [ ] `NOT TESTED` 0.9.30 flagged source sorts below clean sources.


- [ ] `NOT TESTED` 0.9.31 custom dialog has an opaque Apollo background/panel.
- [ ] `NOT TESTED` 0.9.31 underlying Kodi movie list/poster no longer shows through.
- [ ] `NOT TESTED` 0.9.31 row focus and button focus textures render.


- [ ] `NOT TESTED` 0.9.32 OK/Enter plays selected stream directly.
- [ ] `NOT TESTED` 0.9.32 C opens Play + Flag/Unflag context menu.
- [ ] `NOT TESTED` 0.9.32 bundled flag icon renders for flagged row.
- [ ] `NOT TESTED` 0.9.32 no bottom-button navigation is required.


- [ ] `NOT TESTED` 0.9.33 detector no longer treats Kodi window dimensions as max resolution.
- [ ] `NOT TESTED` 0.9.33 detector reports active display mode when Kodi exposes it.
- [ ] `NOT TESTED` 0.9.33 4K toggle is based on display mode, not window size.


- [ ] `NOT TESTED` 0.9.34 device detection preserves all resolution toggles.
- [ ] `NOT TESTED` 0.9.34 summary says Resolution: manual instead of treating GUI size as capability.


- [ ] `NOT TESTED` 0.9.35 compatibility wizard asks resolution first.
- [ ] `NOT TESTED` 0.9.35 review checklist preselects auto-detected HDR/video/audio capabilities.
- [ ] `NOT TESTED` 0.9.35 checklist toggles can be edited before applying.
- [ ] `NOT TESTED` 0.9.35 cancelling either wizard step leaves current settings unchanged.
- [ ] `NOT TESTED` 0.9.35 submitting wizard saves resolution + reviewed capabilities.


- [ ] `NOT TESTED` 0.9.36 compatibility checklist shows HDR / Video Codecs / Audio Formats separators.
- [ ] `NOT TESTED` 0.9.36 selecting a separator row does not affect saved compatibility settings.


- [ ] `NOT TESTED` 0.9.37 restored stream chooser background/panel/focus assets render.
- [ ] `NOT TESTED` 0.9.37 flag badge image still renders.

- [ ] `NOT TESTED` 0.9.38 Current Stream Info shows provider and exact Apollo source title.
- [ ] `NOT TESTED` 0.9.38 Current Stream Info shows correct N-of-total source position.
- [ ] `NOT TESTED` 0.9.38 Current Stream Info reports flag state/reason correctly.
- [ ] `NOT TESTED` compare Current Stream Info against top unflagged chooser row for auto-play ranking validation.

- [ ] `NOT TESTED` 0.9.39 remote movie progress appears in Popular / Trending / Search.
- [ ] `NOT TESTED` 0.9.39 remote episode progress appears in discovery episode lists.
- [ ] `NOT TESTED` 0.9.39 normal remote click with progress asks Resume vs Start from beginning.
- [ ] `NOT TESTED` 0.9.39 Start from beginning clears remote Apollo progress and starts at 0.
- [ ] `NOT TESTED` 0.9.39 remote item without progress auto-plays without a prompt.
- [ ] `NOT TESTED` 0.9.39 Current Stream heading shows provider and N/total.

- [ ] `NOT TESTED` 0.9.40 same remote movie shows identical progress in Popular, Trending and Search.
- [ ] `NOT TESTED` 0.9.40 Trending Movies uses normalized MediaService renderer.
- [ ] `NOT TESTED` 0.9.40 Trending Shows uses normalized MediaService renderer.


## 0.9.53 show-row episode context
- [ ] Local Library Shows display `Sx Ex · Episode Title` beneath the show title.
- [ ] Popular Shows display episode context while remaining show folders.
- [ ] Trending Shows display episode context while remaining show folders.
- [ ] Movies remain unchanged.
- [ ] Opening a show still navigates to Seasons.
- [ ] Library Shows remains acceptably fast; local hints use one batched episode query.


## 0.9.54 versioned show-row episode context

- [ ] `NOT TESTED` Library Shows displays episode context beneath show title where available.
- [ ] `NOT TESTED` Popular Shows displays episode context beneath show title where available.
- [ ] `NOT TESTED` Trending Shows displays episode context beneath show title where available.
- [ ] `NOT TESTED` Show folders still open normally and movies/Continue Watching remain unchanged.


## 0.9.55 canonical feeds + Library Home

- [ ] `NOT TESTED` Media Home row order is Continue Watching, Up Next, Trending Shows, Trending Movies, Popular Shows, Popular Movies.
- [ ] `NOT TESTED` Up Next is empty rather than fabricated before Trakt.
- [ ] `NOT TESTED` Trending rows remain empty rather than using Cinemeta Featured/IMDb-rating semantics.
- [ ] `NOT TESTED` Library Home shows Recently Released Episodes, Recently Added Shows, Recently Released Movies, Recently Added Movies.
- [ ] `NOT TESTED` Recently Released Episodes opens the canonical full-card Episode Detail and exposes show/season links.
- [ ] `NOT TESTED` Recently Added Shows opens Show Detail and does not impersonate an episode.
- [ ] `NOT TESTED` Library Shows sort supports last episode added both directions without an N+1 Jellyfin query.
- [ ] `NOT TESTED` Library Movies sort excludes show-only options.
- [ ] `NOT TESTED` Global in-library indicator appears for local discovery items and library content.
- [ ] `NOT TESTED` Existing Resume/Start Over/Try Next/Now Playing/CW reconciliation behavior remains unchanged.


## 0.9.56 global detail shell cleanup

- [ ] `NOT TESTED` Library → Movies populates without requiring a full media refresh when its sensor starts empty.
- [ ] `NOT TESTED` CW movie detail fills the full card region above nav/mini-player.
- [ ] `NOT TESTED` Show, Season, Episode, and Movie detail share the same full-card shell.
- [ ] `NOT TESTED` Season detail shows parent show title + Season N + optional season summary, never first-episode header metadata.
- [ ] `NOT TESTED` Show → Season → Episode Back navigation restores each prior level.
- [ ] `NOT TESTED` CW local and remote episodes expose show and season links when canonical identity exists.
- [ ] `NOT TESTED` Remove from Continue Watching clears the item and refreshes the CW rail without changing playback contracts.


## 0.9.57 Library Movies + headless CW removal

- [ ] `NOT TESTED` Library → Movies renders from a populated sensor without manual refresh.
- [ ] `NOT TESTED` Card Remove from Continue Watching does not crash or navigate Kodi.
- [ ] `NOT TESTED` Successful card removal disappears immediately, then remains gone after CW refresh.
- [ ] `NOT TESTED` Kodi-native Remove from Continue Watching still refreshes the Kodi directory.
- [ ] `NOT TESTED` Episode Detail shows prominent Show title with Season directly beneath.


## 0.9.58 canonical detail router + headless removal

- [ ] `NOT TESTED` Library → Movies renders when sensor.apollo_library_movies is populated.
- [ ] `NOT TESTED` Card Remove from Continue Watching leaves Kodi UI completely unchanged.
- [ ] `NOT TESTED` Card CW removal disappears optimistically and remains gone after authoritative refresh.
- [ ] `NOT TESTED` CW Episode → Season and Show → Season render the same season and exact episode list.
- [ ] `NOT TESTED` Season detail links to Show and Back returns to its exact origin.
- [ ] `NOT TESTED` Season detail never displays originating episode synopsis/progress.
- [ ] `NOT TESTED` Episode → Season list contains only the selected season in episode-number order.


## 0.9.61 canonical playback lifecycle

- [ ] `NOT TESTED` Local Resume uses the canonical PlaybackSession requested start.
- [ ] `NOT TESTED` Remote Resume uses the same requested-start lifecycle.
- [ ] `NOT TESTED` Local Start Over begins at zero without a second zero seek.
- [ ] `NOT TESTED` Remote Start Over behaves identically.
- [ ] `NOT TESTED` Seek then immediate Stop commits the final checkpoint.
- [ ] `NOT TESTED` Local direct playback writes final progress to Jellyfin.
- [ ] `NOT TESTED` Remote override of a local item writes the same final progress to Jellyfin.
- [ ] `NOT TESTED` Remote-only playback writes final progress to Apollo.
- [ ] `NOT TESTED` Try Next uses the generic live requested-start lifecycle.
- [ ] `NOT TESTED` Playback-error failover uses the same lifecycle.
