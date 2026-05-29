#!/usr/bin/env bash
# Build StockWatch.app with bundled backend and create a DMG (macOS only).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "ERROR: DMG builds must run on macOS." >&2
  exit 1
fi

APP_NAME="StockWatch"
VERSION="${VERSION:-1.0.0}"
BUILD_DIR="$ROOT/build"
DIST_DIR="$BUILD_DIR/dist"
DERIVED="$BUILD_DIR/DerivedData"
PY_DIST="$BUILD_DIR/pyinstaller/stockwatch-backend"

echo "==> Python backend (PyInstaller)"
python3 -m venv "$BUILD_DIR/venv"
# shellcheck disable=SC1091
source "$BUILD_DIR/venv/bin/activate"
pip install -q -r packaging/requirements-build.txt
pyinstaller packaging/stockwatch-backend.spec --noconfirm --distpath "$BUILD_DIR/pyinstaller/dist" --workpath "$BUILD_DIR/pyinstaller/work"

BACKEND_SRC="$BUILD_DIR/pyinstaller/dist/stockwatch-backend"
if [[ ! -d "$BACKEND_SRC" ]]; then
  echo "PyInstaller output missing at $BACKEND_SRC" >&2
  exit 1
fi

echo "==> Xcode Release build"
xcodebuild \
  -project macos/StockWatch/StockWatch.xcodeproj \
  -scheme StockWatch \
  -configuration Release \
  -derivedDataPath "$DERIVED" \
  CODE_SIGN_IDENTITY="${CODE_SIGN_IDENTITY:--}" \
  CODE_SIGNING_ALLOWED=NO \
  build

APP="$DERIVED/Build/Products/Release/${APP_NAME}.app"
if [[ ! -d "$APP" ]]; then
  echo "App bundle not found: $APP" >&2
  exit 1
fi

echo "==> Embed backend"
DEST_BACKEND="$APP/Contents/Resources/backend"
rm -rf "$DEST_BACKEND"
mkdir -p "$DEST_BACKEND"
cp -R "$BACKEND_SRC/"* "$DEST_BACKEND/"
chmod +x "$DEST_BACKEND/stockwatch-backend"

echo "==> Create DMG"
mkdir -p "$DIST_DIR"
DMG_PATH="$DIST_DIR/${APP_NAME}-${VERSION}.dmg"
STAGE="$BUILD_DIR/dmg-stage"
rm -rf "$STAGE"
mkdir -p "$STAGE"
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"

hdiutil create -volname "$APP_NAME" -srcfolder "$STAGE" -ov -format UDZO "$DMG_PATH"
rm -rf "$STAGE"

echo ""
echo "Done: $DMG_PATH"
echo "Open the DMG, drag StockWatch to Applications, then launch StockWatch."
