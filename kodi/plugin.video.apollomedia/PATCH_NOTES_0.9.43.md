# Apollo Media 0.9.43 — Single Resume Decision and Action Chooser

Remote resume:
- Final remote playable items no longer attach Kodi `ResumePoint` metadata when Apollo has already supplied an explicit start position.
- Explicit Apollo decisions use `StartOffset`, including an explicit zero for Start from beginning.
- Native resume metadata remains available on directory/list items and on playable items where Apollo has not made an explicit decision.

Remote stream chooser:
- Every Choose Remote Stream entry point now launches `choose_external` with `RunPlugin` instead of `Container.Update`.
- The chooser remains an action/dialog route and no longer takes over the current Kodi directory.
- Selected playback continues through the dedicated `PlayMedia(...play_session_stream&index=...)` route introduced in 0.9.42.

No source-session, flag, ranking, provider, canonical progress, Jellyfin synchronization, normal-click routing, chooser styling, removal, or completion behavior changed.
