# Apollo Media 0.9.35 — Device Compatibility Wizard

`Detect Device Compatibility` is now a reviewable wizard:

1. Choose display resolution manually:
   - 2160p / 4K
   - 1080p
   - 720p
   - 480p
2. Apollo runs automatic HDR, video-codec and audio-format detection.
3. Kodi opens a native multi-select checklist with detected capabilities
   preselected.
4. The user may toggle any capability before submitting.
5. OK applies the complete profile; cancelling either step changes nothing.

Other changes:
- compatibility detection is now side-effect free until the wizard is submitted;
- unreliable Kodi GUI/window dimensions are no longer part of the workflow;
- the final saved device summary records the manually selected resolution.
