#!/bin/zsh
# Creates "Gnome Connection Manager.app" so macOS shows GCM's own name and icon instead of Python's.
set -e

GCM_DIR="${0:A:h:h}"
VENV_PYTHON="$GCM_DIR/venv/bin/python"
APP_DIR="${1:-$HOME/Applications}/Gnome Connection Manager.app"

if [[ ! -x "$VENV_PYTHON" ]]; then
    echo "error: $VENV_PYTHON not found; create the virtual environment first (see MACOS.md)" >&2
    exit 1
fi

PYTHON_APP_BIN="$("$VENV_PYTHON" -c 'import sys; print(sys.base_prefix)')/Resources/Python.app/Contents/MacOS/Python"
if [[ ! -x "$PYTHON_APP_BIN" ]]; then
    echo "error: $PYTHON_APP_BIN not found; the venv must use a framework build of Python, such as Homebrew's" >&2
    exit 1
fi

VERSION="$(sed -n 's/^app_version = "\(.*\)"/\1/p' "$GCM_DIR/gnome_connection_manager.py")"

rm -rf "$APP_DIR"
mkdir -p "$APP_DIR/Contents/MacOS" "$APP_DIR/Contents/Resources"

# macOS takes the app's name and icon from the bundle the running executable lives in
ln -s "$PYTHON_APP_BIN" "$APP_DIR/Contents/MacOS/python"

# Login shell so terminals opened from Finder get the same PATH as Terminal.app;
# __PYVENV_LAUNCHER__ is how Python.app's own launcher tells the interpreter which venv to use.
# GCM's built-in strings are Spanish, so languages without a translation in lang/ fall back to English.
cat > "$APP_DIR/Contents/MacOS/gnome-connection-manager" <<EOF
#!/bin/zsh -l
export __PYVENV_LAUNCHER__=${(q)VENV_PYTHON}
if [[ -z "\$LANG" || "\$LANG" == C* ]]; then
    locale="\$(defaults read -g AppleLocale 2>/dev/null | cut -d@ -f1)"
    language="\${locale%%_*}"
    if [[ -z "\$language" || ( "\$language" != es && ! -d ${(q)GCM_DIR}/lang/"\$language" ) ]]; then
        locale=en_US
    fi
    export LANG="\$locale.UTF-8"
fi
exec "\${0:A:h}/python" ${(q)GCM_DIR}/gnome_connection_manager.py "\$@"
EOF
chmod +x "$APP_DIR/Contents/MacOS/gnome-connection-manager"

cat > "$APP_DIR/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key><string>Gnome Connection Manager</string>
    <key>CFBundleIdentifier</key><string>com.kuthulu.gnome-connection-manager</string>
    <key>CFBundleExecutable</key><string>gnome-connection-manager</string>
    <key>CFBundleIconFile</key><string>gcm.icns</string>
    <key>CFBundlePackageType</key><string>APPL</string>
    <key>CFBundleShortVersionString</key><string>$VERSION</string>
    <key>CFBundleVersion</key><string>$VERSION</string>
    <key>NSHighResolutionCapable</key><true/>
</dict>
</plist>
EOF

ICONSET="$(mktemp -d)/gcm.iconset"
mkdir -p "$ICONSET"
for size in 16 32 128 256 512; do
    sips -z $size $size "$GCM_DIR/icon.png" --out "$ICONSET/icon_${size}x${size}.png" >/dev/null
    sips -z $((size * 2)) $((size * 2)) "$GCM_DIR/icon.png" --out "$ICONSET/icon_${size}x${size}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o "$APP_DIR/Contents/Resources/gcm.icns"
rm -rf "${ICONSET:h}"

echo "Created $APP_DIR"
