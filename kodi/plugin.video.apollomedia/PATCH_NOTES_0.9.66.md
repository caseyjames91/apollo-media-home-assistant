# Apollo Media 0.9.66 — Playback Source Policy + Technical Context

## Framework status
0.9.65 stream-picker/source-session behavior is preserved and extended. This release focuses on source policy and state plumbing, not final visual styling.

## Remote-first card playback
- The Apollo card now prefers the addon-owned remote playback target whenever a playable item has one.
- Local library items still retain their Jellyfin playback target.
- Local movie/episode details expose `Play Locally` / `Resume Locally` as an explicit fallback.
- This changes card playback policy only; Kodi's native addon browsing behavior is left stable for now.

## Bidirectional live handoff
- Local -> Remote preserves the current absolute playback position.
- Remote -> Local is now available whenever the remote session originated from a Jellyfin library item.
- Remote -> Local also preserves the current absolute playback position through the shared PlaybackSession live-resume path.
- The same Now Playing modal stays open and dynamically changes source controls.

## Stream picker
- Fixed the picker sheet overlapping/cutting off behind the persistent bottom navigation.
- Streams are grouped under quality separators:
  - 4K / 2160p
  - 1080p
  - 720p
  - SD / 480p
  - Other
- Quality grouping metadata is produced by the addon/source session, not inferred by the card.
- Stream rows surface video/audio summary metadata where available.

## Now Playing technical context
- Active Apollo playback now carries video quality, video codec/HDR summary, and audio codec/channel summary.
- Kodi's actual current video/audio stream metadata is used when available.
- For remote playback, parsed ranked-source metadata is used as a fallback.
- The Now Playing modal renders separate VIDEO and AUDIO indicators.

## Detail progress responsiveness
- While card-initiated playback is active, Apollo continuously updates the in-memory canonical identity progress.
- If the matching movie/episode detail progress block is currently open, its watched/remaining/progress values update without requiring a back-out/reopen cycle.
- Existing persistence/reconciliation behavior remains authoritative after playback stops.

## Preserved
- 0.9.63 resume/playback foundation.
- 0.9.64 persistent refresh feedback.
- 0.9.65 headless stream picker, source ranking, Try Next, and flagging.
