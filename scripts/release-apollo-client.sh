#!/usr/bin/env bash
set -euo pipefail

CHECK_ONLY=false

if [[ $# -eq 2 && "$1" == "--check" ]]; then
  CHECK_ONLY=true
  VERSION="$2"
elif [[ $# -eq 1 ]]; then
  VERSION="$1"
else
  echo "Usage:" >&2
  echo "  ./scripts/release-apollo-client.sh --check X.Y.Z" >&2
  echo "  ./scripts/release-apollo-client.sh X.Y.Z" >&2
  exit 2
fi
ROOT="$(git rev-parse --show-toplevel)"
HACS_REPO="${APOLLO_HACS_REPO:-/home/apollo/apollo-media-card}"

cd "$ROOT"

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

echo "== Apollo Media client release $VERSION =="

# ---------------------------------------------------------
# Preconditions
# ---------------------------------------------------------
[[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] \
  || fail "Version must look like X.Y.Z"

command -v git >/dev/null || fail "git not found"
command -v gh >/dev/null || fail "gh not found"
command -v python3 >/dev/null || fail "python3 not found"

gh auth status >/dev/null 2>&1 \
  || fail "GitHub CLI is not authenticated"

[[ -d "$HACS_REPO/.git" ]] \
  || fail "HACS repo not found at $HACS_REPO"

if [[ -n "$(git status --porcelain)" ]]; then
  fail "Monorepo working tree is not clean"
fi

if [[ -n "$(git -C "$HACS_REPO" status --porcelain)" ]]; then
  fail "HACS repo working tree is not clean"
fi

git fetch origin --tags
git -C "$HACS_REPO" fetch origin --tags

[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] \
  || fail "Monorepo main is not synchronized with origin/main"

[[ "$(git -C "$HACS_REPO" rev-parse HEAD)" == \
   "$(git -C "$HACS_REPO" rev-parse origin/main)" ]] \
  || fail "HACS repo main is not synchronized with origin/main"

if [[ "$CHECK_ONLY" == false ]]; then
  if git rev-parse "$VERSION" >/dev/null 2>&1; then
    fail "Monorepo tag $VERSION already exists"
  fi

  if git -C "$HACS_REPO" rev-parse "$VERSION" >/dev/null 2>&1; then
    fail "HACS tag $VERSION already exists"
  fi

  if gh release view "$VERSION" >/dev/null 2>&1; then
    fail "Monorepo GitHub release $VERSION already exists"
  fi

  if gh release view "$VERSION" \
    -R caseyjames91/apollo-media-card >/dev/null 2>&1; then
    fail "HACS GitHub release $VERSION already exists"
  fi
fi

if [[ "$CHECK_ONLY" == true ]]; then
  CURRENT_VERSION="$(python3 - <<'PY2'
import xml.etree.ElementTree as ET
print(ET.parse("kodi/plugin.video.apollomedia/addon.xml").getroot().attrib["version"])
PY2
)"

  python3 -m unittest discover \
    -s kodi/plugin.video.apollomedia/tests \
    -p 'test_*.py'

  python3 scripts/verify-project.py
  git diff --check

  [[ -f "dist/apollo-media-card.js" ]] \
    || fail "Canonical HACS card distribution is missing"

  cmp -s     dist/apollo-media-card.js     "$HACS_REPO/dist/apollo-media-card.js" \
    || fail "HACS repository card differs from canonical dist card"

  echo
  echo "PASS: release preflight"
  echo "  Current source version: $CURRENT_VERSION"
  echo "  Requested release:      $VERSION"
  echo "  Monorepo:               clean and synchronized"
  echo "  HACS repo:              clean and synchronized"
  echo "  Tests/project:          verified"
  echo "  Card distribution:      synchronized"
  exit 0
fi

# ---------------------------------------------------------
# Update canonical release version
# ---------------------------------------------------------
python3 - "$VERSION" <<'PY'
from pathlib import Path
import re
import sys

version = sys.argv[1]

addon = Path("kodi/plugin.video.apollomedia/addon.xml")
text = addon.read_text(encoding="utf-8")

new_text, count = re.subn(
    r'(<addon\b[^>]*\bversion=")[0-9]+\.[0-9]+\.[0-9]+(")',
    rf'\g<1>{version}\2',
    text,
    count=1,
)

if count != 1:
    raise SystemExit("ERROR: unable to update addon.xml version")

addon.write_text(new_text, encoding="utf-8")

test = Path(
    "kodi/plugin.video.apollomedia/tests/"
    "test_ams_continue_watching.py"
)
text = test.read_text(encoding="utf-8")

new_text, count = re.subn(
    r'version="[0-9]+\.[0-9]+\.[0-9]+"',
    f'version="{version}"',
    text,
    count=1,
)

if count != 1:
    raise SystemExit("ERROR: unable to update release-version test")

test.write_text(new_text, encoding="utf-8")

print(f"PASS: release version updated to {version}")
PY

# ---------------------------------------------------------
# Validate source before building
# ---------------------------------------------------------
python3 -m unittest discover \
  -s kodi/plugin.video.apollomedia/tests \
  -p 'test_*.py'

# ---------------------------------------------------------
# Preserve historical tracked checksums
# ---------------------------------------------------------
mapfile -t OLD_CHECKSUMS < <(
  git ls-files \
    'kodi-repository/plugin.video.apollomedia/*.zip.sha256'
)

python3 scripts/build-kodi-repository.py

CURRENT_CHECKSUM="kodi-repository/plugin.video.apollomedia/plugin.video.apollomedia-${VERSION}.zip.sha256"

for file in "${OLD_CHECKSUMS[@]}"; do
  if [[ "$file" != "$CURRENT_CHECKSUM" ]]; then
    git restore -- "$file"
  fi
done

python3 scripts/verify-project.py
git diff --check

PACKAGE="kodi-repository/plugin.video.apollomedia/plugin.video.apollomedia-${VERSION}.zip"
CHECKSUM="${PACKAGE}.sha256"

[[ -f "$PACKAGE" ]] || fail "Kodi package was not produced"
[[ -f "$CHECKSUM" ]] || fail "Kodi checksum was not produced"

# ---------------------------------------------------------
# Commit canonical monorepo release
# ---------------------------------------------------------
git add \
  card/apollo-media-card.js \
  dist/apollo-media-card.js \
  kodi/apollo-media-card.js \
  kodi/plugin.video.apollomedia/addon.xml \
  kodi/plugin.video.apollomedia/tests \
  kodi-repository/addons.xml \
  kodi-repository/addons.xml.md5 \
  kodi-repository/plugin.video.apollomedia/addon.xml \
  "$PACKAGE" \
  "$CHECKSUM"

git diff --cached --check

if git diff --cached --quiet; then
  fail "No monorepo release changes found"
fi

git commit -m "Release Apollo Media $VERSION"
git push origin main

git tag -a "$VERSION" -m "Apollo Media $VERSION"
git push origin "$VERSION"

gh release create "$VERSION" \
  --verify-tag \
  --title "Apollo Media $VERSION" \
  --generate-notes \
  --latest

# ---------------------------------------------------------
# Sync dedicated HACS distribution repository
# ---------------------------------------------------------
cp \
  "$ROOT/dist/apollo-media-card.js" \
  "$HACS_REPO/dist/apollo-media-card.js"

cd "$HACS_REPO"

git add dist/apollo-media-card.js

if git diff --cached --quiet; then
  echo "INFO: card JS unchanged; creating version release from current HACS source"
else
  git diff --cached --check
  git commit -m "Release Apollo Media Card $VERSION"
  git push origin main
fi

git tag -a "$VERSION" -m "Apollo Media Card $VERSION"
git push origin "$VERSION"

gh release create "$VERSION" \
  dist/apollo-media-card.js \
  --verify-tag \
  --title "Apollo Media Card $VERSION" \
  --generate-notes \
  --latest \
  -R caseyjames91/apollo-media-card

# ---------------------------------------------------------
# Final verification
# ---------------------------------------------------------
cd "$ROOT"

[[ -z "$(git status --porcelain)" ]] \
  || fail "Monorepo is dirty after release"

[[ -z "$(git -C "$HACS_REPO" status --porcelain)" ]] \
  || fail "HACS repo is dirty after release"

echo
echo "PASS: Apollo Media $VERSION released"
echo "  Kodi repository: $PACKAGE"
echo "  Monorepo release: $VERSION"
echo "  HACS card release: $VERSION"
