#!/bin/sh
set -e

# If config.yaml is missing, initialize from example config
if [ ! -f "/app/config.yaml" ] && [ -z "$JANUS_CONFIG" ]; then
    echo "[janus-entrypoint] No config.yaml mounted at /app/config.yaml. Using default config.example.yaml..."
    cp /app/config.example.yaml /app/config.yaml
fi

# Informative checks on volume mounts
if [ -S "/var/run/dbus/system_bus_socket" ]; then
    echo "[janus-entrypoint] Host DBus socket mounted at /var/run/dbus/system_bus_socket."
else
    echo "[janus-entrypoint] Note: Host DBus socket not mounted. Power operations will operate in simulation mode."
fi

if [ -d "/boot" ] && [ -f "/boot/grub/grubenv" ]; then
    echo "[janus-entrypoint] Host /boot/grub/grubenv detected."
else
    echo "[janus-entrypoint] Note: Host /boot volume not mounted. GRUB OS switching will operate in simulation mode."
fi

exec "$@"
