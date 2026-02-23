#!/usr/bin/env bash
# ============================================================
# OSCAR Linux Build Script
# Produces: dist/OSCAR-3.0.0-Linux.AppImage
#
# Requirements:
#   pip install pyinstaller pywebview cryptography
#   wget "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
#   chmod +x appimagetool-x86_64.AppImage
#   sudo apt-get install libgtk-3-dev libwebkit2gtk-4.0-dev   (Ubuntu/Debian)
#   sudo dnf install gtk3-devel webkit2gtk3-devel              (Fedora)
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ROOT_DIR"

APP_NAME="OSCAR"
APP_VERSION="3.0.0"
DIST_DIR="dist"
APPIMAGE_NAME="${APP_NAME}-${APP_VERSION}-Linux-x86_64.AppImage"

echo "══════════════════════════════════════════"
echo "  Building ${APP_NAME} v${APP_VERSION} for Linux"
echo "══════════════════════════════════════════"

# ── 1. Clean previous build ───────────────────────────────────────────────────
echo "▸ Cleaning..."
rm -rf "dist/OSCAR" "dist/${APPIMAGE_NAME}" AppDir 2>/dev/null || true

# ── 2. PyInstaller ────────────────────────────────────────────────────────────
echo "▸ Running PyInstaller..."
pyinstaller oscar.spec --noconfirm --clean

# ── 3. Build AppImage structure ───────────────────────────────────────────────
echo "▸ Building AppImage structure..."
mkdir -p AppDir/usr/bin
mkdir -p AppDir/usr/share/applications
mkdir -p AppDir/usr/share/icons/hicolor/256x256/apps

cp -r "dist/OSCAR/." "AppDir/usr/bin/"

# Desktop entry
cat > AppDir/usr/share/applications/oscar.desktop << 'EOF'
[Desktop Entry]
Type=Application
Name=OSCAR
Comment=Outil de Suivi des Cours et d'Analyse du Réseau
Exec=OSCAR
Icon=oscar
Categories=Office;Education;
Terminal=false
StartupNotify=true
EOF

# App icon
cp IFI_noir_logo.png AppDir/usr/share/icons/hicolor/256x256/apps/oscar.png
cp IFI_noir_logo.png AppDir/oscar.png

# AppRun script
cat > AppDir/AppRun << 'APPRUN'
#!/bin/bash
SELF=$(readlink -f "$0")
HERE=$(dirname "$SELF")
export PATH="$HERE/usr/bin:$PATH"
export LD_LIBRARY_PATH="$HERE/usr/lib:$LD_LIBRARY_PATH"
exec "$HERE/usr/bin/OSCAR" "$@"
APPRUN
chmod +x AppDir/AppRun

# Desktop file symlink at root (required by AppImage spec)
cp AppDir/usr/share/applications/oscar.desktop AppDir/oscar.desktop

# ── 4. Create AppImage ────────────────────────────────────────────────────────
echo "▸ Creating AppImage..."
APPIMAGETOOL=""
if command -v appimagetool-x86_64.AppImage &> /dev/null; then
    APPIMAGETOOL="appimagetool-x86_64.AppImage"
elif command -v appimagetool &> /dev/null; then
    APPIMAGETOOL="appimagetool"
else
    echo "  appimagetool not found. Download from:"
    echo "  https://github.com/AppImage/AppImageKit/releases"
    echo "  Distributable folder is at: dist/OSCAR/"
    exit 0
fi

ARCH=x86_64 "$APPIMAGETOOL" AppDir "${DIST_DIR}/${APPIMAGE_NAME}"

# ── 5. Cleanup ────────────────────────────────────────────────────────────────
rm -rf AppDir

echo ""
echo "══════════════════════════════════════════"
echo "  ✓ Build complete: ${DIST_DIR}/${APPIMAGE_NAME}"
echo "══════════════════════════════════════════"
