# Apollo Media 0.9.37 — Restore Stream Chooser Assets

- Fixes the custom stream chooser becoming transparent/broken again in later builds.
- Root cause: Apollo's text-only source bundle did not include PNG assets under
  `resources/media/`. Builds 0.9.33+ were reconstructed from that text bundle,
  so the XML still referenced the images but the packaged addon no longer
  contained them.
- Restores:
  - dialog_bg.png
  - dialog_panel.png
  - row_normal.png
  - row_focus.png
  - flagged.png
- No stream ranking, playback, compatibility, resume, or flag logic changed.
- The build process now also emits a complete source ZIP so binary assets are
  preserved for future rebuilds.
