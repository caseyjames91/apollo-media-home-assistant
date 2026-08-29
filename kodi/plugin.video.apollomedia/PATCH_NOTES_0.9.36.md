# Apollo Media 0.9.36 — Compatibility Review Sections

- Adds visual section separators to the native compatibility review checklist:
  - HDR
  - Video Codecs
  - Audio Formats
- Capability labels no longer repeat the group prefix on every row.
- Kodi's native multiselect does not support true disabled section headers,
  so separator rows are deliberately ignored when saving even if Kodi allows
  them to receive focus or be checked.
- Resolution wizard and detection logic are unchanged.
