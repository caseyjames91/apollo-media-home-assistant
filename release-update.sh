#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: ./release-update.sh Apollo-HA-Addon-X.Y.Z-update.zip" >&2
  exit 2
fi

ZIP="$1"
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -z "$ROOT" || "$PWD" != "$ROOT" ]]; then
  echo "ERROR: Run this from the Apollo repository root." >&2
  exit 1
fi
if [[ ! -f "$ZIP" ]]; then
  echo "ERROR: Update ZIP not found: $ZIP" >&2
  exit 1
fi

# Permit only the supplied ZIP as an untracked change before extraction.
mapfile -t dirty < <(git status --porcelain)
for line in "${dirty[@]:-}"; do
  [[ -z "$line" ]] && continue
  path="${line:3}"
  if [[ "$line" == "?? "* && "$path" == "$ZIP" ]]; then
    continue
  fi
  echo "ERROR: Working tree is not clean: $line" >&2
  echo "Commit/stash/remove unrelated changes before releasing." >&2
  exit 1
done

# Verify the archive before touching the tree.
unzip -tq "$ZIP" >/dev/null
if ! unzip -l "$ZIP" | grep -q 'apollo_media_server/config.yaml'; then
  echo "ERROR: ZIP does not look like an Apollo HA add-on update." >&2
  exit 1
fi

unzip -oq "$ZIP"
rm -f "$ZIP"

VERSION="$(awk -F'"' '/^version:/ {print $2; exit}' apollo_media_server/config.yaml)"
if [[ -z "$VERSION" ]]; then
  echo "ERROR: Could not read version from config.yaml." >&2
  exit 1
fi

echo "Apollo Media Server $VERSION changes:"
git status --short

git add .
git diff --cached --check

if git diff --cached --quiet; then
  echo "ERROR: No release changes found." >&2
  exit 1
fi

git commit -m "Release Apollo Media Server $VERSION"
git push

echo
echo "PASS: Apollo Media Server $VERSION committed and pushed."
echo "Home Assistant can now refresh the repository and install the update."
