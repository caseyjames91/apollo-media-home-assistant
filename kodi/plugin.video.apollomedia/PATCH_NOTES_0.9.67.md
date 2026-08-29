# Apollo Media 0.9.67 — Remote Resume Crash Fix

## Root cause
- 0.9.66 added technical stream classification in `resources/lib/source_session.py`.
- `_technical_info()` uses `re.search()` to detect channel layouts such as 5.1/7.1.
- The module did not import Python's `re` module.
- Every remote playback path that created a new source session could therefore fail before playback with:
  `NameError: name 're' is not defined`.

## Fix
- Added the missing `import re` to `resources/lib/source_session.py`.

## Scope
- No playback/resume architecture changed.
- No card behavior changed.
- No Home Assistant behavior changed.
- 0.9.66 remote-first playback policy, quality metadata, stream picker, and bidirectional source switching are otherwise unchanged.
