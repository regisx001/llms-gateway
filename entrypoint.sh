#!/bin/sh
# entrypoint.sh — start llama-server + modelctl-api (FastAPI)

set -e

LLAMA_SERVER=/app/llama-server
LLAMA_PID_FILE=/tmp/llama-server.pid

# ── Start modelctl-api (FastAPI) in background ──────────────────────
# Container port is always 8000. The host port is mapped via docker-compose.
API_PORT=8000
start_modelctl_api() {
    echo "Starting modelctl-api on port $API_PORT..."
    uvicorn modelctl_api.main:app \
        --host 0.0.0.0 \
        --port "$API_PORT" \
        --log-level info &
}

# ── Start llama-server with active model ────────────────────────────
start_llama_server() {
    local model_flag=""
    for link in /models/*.gguf; do
        if [ -L "$link" ] && [ -f "$(readlink -f "$link" 2>/dev/null)" ]; then
            echo "Loading model: $(readlink -f "$link")"
            model_flag="-m $(readlink -f "$link")"
            break
        fi
    done
    if [ -z "$model_flag" ]; then
        echo "No active model symlink found in /models/"
    fi

    $LLAMA_SERVER $model_flag "$@" &
    PID=$!
    echo "$PID" > $LLAMA_PID_FILE
    wait $PID
    rm -f $LLAMA_PID_FILE
}

# ── Start both ──────────────────────────────────────────────────────
start_modelctl_api

echo "Starting llama-server..."
start_llama_server "$@"

# Loop: when llama-server exits (modelctl reload), restart with updated model
while true; do
    echo "Restarting llama-server with updated model..."
    sleep 1
    start_llama_server "$@"
done
