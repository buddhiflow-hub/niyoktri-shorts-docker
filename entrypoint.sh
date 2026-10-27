#!/bin/bash
set -e

echo "=================================================="
echo "⚡ Niyoktri Shorts Factory (Dockerized Edition) ⚡"
echo "=================================================="

# Ensure directories exist inside mounted volume
mkdir -p /app/storage/input \
         /app/storage/output \
         /app/storage/cache/videos \
         /app/storage/cache/audio \
         /app/storage/cache/models \
         /app/storage/secrets

# Update font cache if custom fonts were mounted
if [ -d "/app/assets/fonts" ] && [ "$(ls -A /app/assets/fonts 2>/dev/null)" ]; then
    echo "[Entrypoint] Refreshing font cache..."
    fc-cache -fv > /dev/null 2>&1
fi

echo "[Entrypoint] Storage directories ready. Launching command: $@"
exec "$@"
