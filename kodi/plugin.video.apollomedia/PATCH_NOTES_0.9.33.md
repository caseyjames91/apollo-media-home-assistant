# Apollo Media 0.9.33 — Resolution Detection Fix

- Stops using `System.ScreenWidth` / `System.ScreenHeight` as the device's
  maximum playback resolution.
- Those labels can represent the current Kodi window/render size, which caused
  a windowed 1529×1311 Kodi session to incorrectly disable 4K.
- Resolution detection now prefers Kodi's active display-mode labels:
  - `System.ScreenMode`
  - `System.ScreenResolution`
- Apollo parses the actual mode (for example 3840×2160 or 1920×1080) and uses
  that for 2160p/1080p/720p capability toggles.
- If Kodi does not expose a usable display mode, Apollo preserves the user's
  existing resolution toggles instead of guessing from the GUI window size.
- The detector summary explicitly says when resolution is unknown and may show
  GUI dimensions only as diagnostics.
- HDR, codec and audio detection are unchanged in this build.
