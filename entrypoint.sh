#!/bin/sh
# entrypoint.sh — start modelctl-api (FastAPI)
#
# Model serving is now handled by per-capability inference containers
# orchestrated via modelctl-orch. This container only runs the
# management API (modelctl-api). No legacy symlink-based activation.

set -e

# ── Fix ownership of mounted volumes ───────────────────────────────
# The container runs as root, so any directories it creates inside
# mounted volumes end up owned by root. Fix them on every start.
STORAGE_DIR="${MODELCTL_API_STORAGE_DIR:-/home/regisx001/llms-gateway/storage}"
REGISTRY_DIR="${MODELCTL_API_REGISTRY_DIR:-/home/regisx001/llms-gateway/registry}"
if [ -d "$STORAGE_DIR" ]; then
    chown -R "$(stat -c '%u:%g' "$(dirname "$STORAGE_DIR")")" "$STORAGE_DIR" 2>/dev/null || true
fi
if [ -d "$REGISTRY_DIR" ]; then
    chown -R "$(stat -c '%u:%g' "$(dirname "$REGISTRY_DIR")")" "$REGISTRY_DIR" 2>/dev/null || true
fi

# ── Start modelctl-api (FastAPI) ────────────────────────────────────
API_PORT=8000
echo "Starting modelctl-api on port $API_PORT..."
uvicorn modelctl_api.main:app \
    --host 0.0.0.0 \
    --port "$API_PORT" \
    --log-level info
    sleep 1
    start_llama_server "$@"
done
