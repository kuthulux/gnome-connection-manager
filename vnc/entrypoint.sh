#!/bin/bash
set -e

HOME_DIR=/home/testuser
VNC_DIR="${HOME_DIR}/.vnc"

mkdir -p "${VNC_DIR}"

# Mot de passe VNC
echo "${VNC_PASSWORD}" | vncpasswd -f > "${VNC_DIR}/passwd"
chmod 600 "${VNC_DIR}/passwd"

# Session xfce4
cat > "${VNC_DIR}/xstartup" <<'EOF'
#!/bin/bash
unset SESSION_MANAGER
unset DBUS_SESSION_BUS_ADDRESS
exec startxfce4
EOF
chmod +x "${VNC_DIR}/xstartup"

chown -R testuser:testuser "${HOME_DIR}"

# dbus
mkdir -p /run/dbus
dbus-daemon --system --fork 2>/dev/null || true

echo "[entrypoint] Démarrage TigerVNC sur ${VNC_DISPLAY} — geometry=${VNC_GEOMETRY} depth=${VNC_DEPTH}"

exec su -c "vncserver ${VNC_DISPLAY} \
    -geometry ${VNC_GEOMETRY} \
    -depth ${VNC_DEPTH} \
    -fg \
    -localhost no \
    -SecurityTypes VncAuth \
    -PasswordFile ${VNC_DIR}/passwd" testuser
