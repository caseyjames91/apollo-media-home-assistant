#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-.}"
CFG="$ROOT/apollo_media_server/config.yaml"
DOCKERFILE="$ROOT/apollo_media_server/Dockerfile"
VERSION="$(awk -F'"' '/^version:/ {print $2; exit}' "$CFG")"
[[ -n "$VERSION" ]] || { echo "ERROR: missing config version" >&2; exit 1; }
grep -q '^ARG BUILD_VERSION$' "$DOCKERFILE" || { echo "ERROR: Dockerfile missing ARG BUILD_VERSION" >&2; exit 1; }
grep -q '^ENV APOLLO_VERSION=${BUILD_VERSION}$' "$DOCKERFILE" || { echo "ERROR: Dockerfile does not export BUILD_VERSION as APOLLO_VERSION" >&2; exit 1; }
python3 - "$ROOT" <<'PY'
from pathlib import Path
import re, sys
root = Path(sys.argv[1])
pat = re.compile(r'(["\'])0\.\d+\.\d+\1')
bad=[]
for p in (root/'apollo_media_server'/'app').rglob('*.py'):
    for n,line in enumerate(p.read_text().splitlines(),1):
        if pat.search(line): bad.append(f"{p}:{n}:{line.strip()}")
p=root/'apollo_media_server'/'run.sh'
for n,line in enumerate(p.read_text().splitlines(),1):
    if pat.search(line): bad.append(f"{p}:{n}:{line.strip()}")
if bad:
    print("ERROR: hard-coded runtime semantic version found:", file=sys.stderr)
    print("\n".join(bad), file=sys.stderr)
    raise SystemExit(1)
PY
printf 'PASS: release version %s is config-driven at runtime.\n' "$VERSION"
