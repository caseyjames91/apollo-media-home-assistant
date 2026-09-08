#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
docker build -t ava-ir-bridge-builder .
docker run --rm -v "$PWD:/src" ava-ir-bridge-builder
APK="$PWD/app/build/outputs/apk/debug/app-debug.apk"
echo
echo "Built: $APK"
echo "Install with: adb install -r '$APK'"
