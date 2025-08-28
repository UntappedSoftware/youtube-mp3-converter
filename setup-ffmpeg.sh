#!/usr/bin/env bash
set -euo pipefail

TARGET_DIR="youtube-mp3-converter/frontend/static/ffmpeg"
mkdir -p "$TARGET_DIR"

echo "📦 Installing @ffmpeg/ffmpeg and @ffmpeg/core (if not already)..."
npm install @ffmpeg/ffmpeg @ffmpeg/core --no-audit --no-fund

echo "🔎 Searching for a usable FFmpeg JS build in node_modules..."
# candidate paths to check (covers common layouts and versions)
candidates=(
  "node_modules/@ffmpeg/ffmpeg/dist/ffmpeg.min.js"
  "node_modules/@ffmpeg/ffmpeg/dist/ffmpeg.js"
  "node_modules/@ffmpeg/ffmpeg/dist/ffmpeg.mjs"
  "node_modules/@ffmpeg/ffmpeg/dist/esm/ffmpeg.js"
  "node_modules/@ffmpeg/ffmpeg/dist/esm/ffmpeg.mjs"
  "node_modules/@ffmpeg/ffmpeg/dist/umd/ffmpeg.js"
  "node_modules/@ffmpeg/ffmpeg/dist/umd/ffmpeg.min.js"
  "node_modules/@ffmpeg/ffmpeg/dist/ffmpeg.esm.js"
)

FFJS=""
for p in "${candidates[@]}"; do
  if [ -f "$p" ]; then
    FFJS="$p"
    break
  fi
done

# fallback to find if none matched
if [ -z "$FFJS" ]; then
  FFJS=$(find node_modules/@ffmpeg/ffmpeg -type f -name "ffmpeg*.js" -print -quit 2>/dev/null || true)
fi

if [ -z "$FFJS" ]; then
  echo "❌ Could not find an FFmpeg JS file automatically. Listing node_modules/@ffmpeg/ffmpeg:"
  ls -la node_modules/@ffmpeg/ffmpeg || true
  exit 1
fi

echo "✅ Found FFmpeg JS: $FFJS"
cp "$FFJS" "$TARGET_DIR/ffmpeg.js"

echo "🔎 Searching for core (ffmpeg-core.*) files..."
CORE_JS=""
CORE_WASM=""

# Try common core package names
for pkg in "@ffmpeg/core" "@ffmpeg/core-mt" "@ffmpeg/core-wasm"; do
  if [ -d "node_modules/$pkg" ]; then
    CORE_JS=$(find "node_modules/$pkg" -maxdepth 3 -type f -name "ffmpeg-core*.js" -print -quit || true)
    CORE_WASM=$(find "node_modules/$pkg" -maxdepth 3 -type f -name "ffmpeg-core*.wasm" -print -quit || true)
    if [ -n "$CORE_JS" ] || [ -n "$CORE_WASM" ]; then
      break
    fi
  fi
done

# fallback global search
if [ -z "$CORE_JS" ]; then
  CORE_JS=$(find node_modules -type f -path "*/@ffmpeg/*/dist/*ffmpeg-core*.js" -print -quit 2>/dev/null || true)
fi
if [ -z "$CORE_WASM" ]; then
  CORE_WASM=$(find node_modules -type f -path "*/@ffmpeg/*/dist/*ffmpeg-core*.wasm" -print -quit 2>/dev/null || true)
fi

if [ -z "$CORE_JS" ] || [ -z "$CORE_WASM" ]; then
  echo "❌ Could not find both core JS and core WASM files automatically."
  echo "Searched for:"
  echo "  core JS => $CORE_JS"
  echo "  core WASM => $CORE_WASM"
  echo ""
  echo "Run this to inspect possible files:"
  echo "  ls -R node_modules/@ffmpeg | sed -n '1,200p'"
  exit 1
fi

echo "✅ Found core JS: $CORE_JS"
echo "✅ Found core WASM: $CORE_WASM"

cp "$CORE_JS" "$TARGET_DIR/ffmpeg-core.js"
cp "$CORE_WASM" "$TARGET_DIR/ffmpeg-core.wasm"

echo "🎉 Done. Files copied to: $TARGET_DIR"
echo " - $TARGET_DIR/ffmpeg.js"
echo " - $TARGET_DIR/ffmpeg-core.js"
echo " - $TARGET_DIR/ffmpeg-core.wasm"
