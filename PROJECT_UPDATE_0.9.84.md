# Apollo project update 0.9.84

This overlay keeps the existing Home Assistant add-on repository layout and adds:

- `kodi/` — canonical Kodi add-on source and tests.
- `kodi-repository/` — installable Apollo Kodi repository plus Apollo Media 0.9.84.
- `card/` — canonical card source.
- `dist/` + `hacs.json` — HACS Dashboard distribution.
- `.github/workflows/validate.yml` — HACS, Python, and JS validation.
- `scripts/build-kodi-repository.py` and `scripts/verify-project.py` — reproducible distribution tooling.

0.9.84 also fixes AMS artwork disappearing and suppresses no-op Continue Watching rail replacement.
