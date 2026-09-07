#!/bin/bash
set -euo pipefail
DATA_DIR="/var/lib/recipes/remote-desktop"
mkdir -p "$DATA_DIR"

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y \
  tigervnc-standalone-server tigervnc-common \
  novnc websockify dbus-x11 \
  xfce4 xfce4-terminal firefox-esr

cat > "$DATA_DIR/xstartup" << 'EOF'
#!/bin/sh
unset SESSION_MANAGER
exec dbus-launch --exit-with-session startxfce4
EOF
chmod +x "$DATA_DIR/xstartup"

# noVNC ships no index.html, so / would 404 - redirect it to vnc.html.
echo '<meta http-equiv="refresh" content="0; url=vnc.html?autoconnect=true&resize=scale">' \
  > /usr/share/novnc/index.html
