#!/usr/bin/env bash
# ============================================================
# OSCAR macOS Build Script
# Produces: dist/OSCAR.dmg
#
# Requirements:
#   brew install create-dmg
#   pip install pyinstaller pywebview cryptography
#
# For notarization (removes "unverified developer" warning):
#   export APPLE_ID="your@apple.id"
#   export APPLE_TEAM_ID="XXXXXXXXXX"
#   export APPLE_APP_PASSWORD="xxxx-xxxx-xxxx-xxxx"  # app-specific password
#   export CODESIGN_IDENTITY="Developer ID Application: Your Name (XXXXXXXXXX)"
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ROOT_DIR"

APP_NAME="OSCAR"
APP_VERSION="3.0.0"
DIST_DIR="dist"
DMG_NAME="${APP_NAME}-${APP_VERSION}-macOS.dmg"

echo "══════════════════════════════════════════"
echo "  Building ${APP_NAME} v${APP_VERSION} for macOS"
echo "══════════════════════════════════════════"

# ── 1. Convert icon ───────────────────────────────────────────────────────────
echo "▸ Converting icon..."
mkdir -p build/icons
ICONSET="build/icons/oscar.iconset"
mkdir -p "$ICONSET"

# Use sips (built-in macOS) to generate all required sizes
for SIZE in 16 32 64 128 256 512 1024; do
    sips -z "$SIZE" "$SIZE" IFI_noir_logo.png --out "${ICONSET}/icon_${SIZE}x${SIZE}.png" > /dev/null 2>&1
done
# @2x variants
for SIZE in 16 32 64 128 256 512; do
    SIZE2=$((SIZE * 2))
    sips -z "$SIZE2" "$SIZE2" IFI_noir_logo.png --out "${ICONSET}/icon_${SIZE}x${SIZE}@2x.png" > /dev/null 2>&1
done
iconutil -c icns "$ICONSET" -o build/icons/oscar.icns
echo "  ✓ oscar.icns created"

# ── 2. Clean previous build ───────────────────────────────────────────────────
echo "▸ Cleaning previous build..."
rm -rf build/OSCAR build/OSCAR.app dist/OSCAR dist/OSCAR.app "$DIST_DIR/${DMG_NAME}" 2>/dev/null || true

# ── 3. PyInstaller ────────────────────────────────────────────────────────────
echo "▸ Running PyInstaller..."
pyinstaller oscar.spec --noconfirm --clean

# ── 4. Code signing ───────────────────────────────────────────────────────────
# Always do ad-hoc signing (free) to handle nested dylibs/frameworks.
# For distribution, set CODESIGN_IDENTITY to your Apple Developer ID.
echo "▸ Ad-hoc signing bundle components..."
find "dist/${APP_NAME}.app" -name "*.dylib" -o -name "*.so" | \
    xargs -I {} codesign --force --sign - "{}" 2>/dev/null || true
find "dist/${APP_NAME}.app" -name "*.framework" -maxdepth 8 | sort -r | \
    xargs -I {} codesign --force --sign - "{}" 2>/dev/null || true
codesign --force --sign - "dist/${APP_NAME}.app" 2>&1 || true
echo "  ✓ Ad-hoc signed"

if [ -n "${CODESIGN_IDENTITY:-}" ]; then
    echo "▸ Code signing..."
    codesign --deep --force --verify --verbose \
        --sign "$CODESIGN_IDENTITY" \
        --options runtime \
        --entitlements build/entitlements.plist \
        "dist/${APP_NAME}.app"
    echo "  ✓ Signed with: $CODESIGN_IDENTITY"
else
    echo "  ℹ Skipping code signing (CODESIGN_IDENTITY not set)"
fi

# ── 5. Create DMG ─────────────────────────────────────────────────────────────
echo "▸ Creating DMG..."
mkdir -p "$DIST_DIR"
create-dmg \
    --volname "$APP_NAME" \
    --volicon "build/icons/oscar.icns" \
    --window-pos 200 120 \
    --window-size 600 400 \
    --icon-size 100 \
    --icon "${APP_NAME}.app" 175 190 \
    --hide-extension "${APP_NAME}.app" \
    --app-drop-link 425 190 \
    --background "build/dmg_background.png" \
    "${DIST_DIR}/${DMG_NAME}" \
    "dist/${APP_NAME}.app" \
    2>/dev/null || \
create-dmg \
    --volname "$APP_NAME" \
    --window-size 600 400 \
    --icon-size 100 \
    --icon "${APP_NAME}.app" 175 190 \
    --app-drop-link 425 190 \
    "${DIST_DIR}/${DMG_NAME}" \
    "dist/${APP_NAME}.app"

# ── 6. Notarize (optional) ───────────────────────────────────────────────────
if [ -n "${APPLE_ID:-}" ] && [ -n "${APPLE_TEAM_ID:-}" ] && [ -n "${APPLE_APP_PASSWORD:-}" ]; then
    echo "▸ Notarizing DMG..."
    xcrun notarytool submit "${DIST_DIR}/${DMG_NAME}" \
        --apple-id "$APPLE_ID" \
        --team-id "$APPLE_TEAM_ID" \
        --password "$APPLE_APP_PASSWORD" \
        --wait
    xcrun stapler staple "${DIST_DIR}/${DMG_NAME}"
    echo "  ✓ Notarized and stapled"
else
    echo "  ℹ Skipping notarization (APPLE_ID/APPLE_TEAM_ID/APPLE_APP_PASSWORD not set)"
fi

echo ""
echo "══════════════════════════════════════════"
echo "  ✓ Build complete: ${DIST_DIR}/${DMG_NAME}"
echo "══════════════════════════════════════════"
