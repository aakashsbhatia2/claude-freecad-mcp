#!/usr/bin/env bash
# One-time: fetch the FreeCAD AppImage this project runs against.
set -euo pipefail
cd "$(dirname "$0")"

URL="https://github.com/FreeCAD/FreeCAD/releases/download/1.1.3/FreeCAD_1.1.3-Linux-x86_64-py311.AppImage"
SHA="3a853eb69ee595f779f2255dbf80a765926981d8ff68903cefee4dfb03a8f5ef"
OUT="vendor/FreeCAD_1.1.3-x86_64.AppImage"

mkdir -p vendor
[ -f "$OUT" ] || curl -L --progress-bar -o "$OUT" "$URL"
echo "$SHA  $OUT" | sha256sum -c -
chmod +x "$OUT"
