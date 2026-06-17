#!/bin/sh
# entrypoint.sh — start llama-server with active model, reload on SIGTERM

LLAMA_SERVER=/app/llama-server
PID_FILE=/tmp/llama-server.pid

start_server() {
    local model_flag=""
    # Find any .gguf symlink (named after the model_id)
    for link in /models/*.gguf; do
        if [ -L "$link" ] && [ -f "$(readlink -f "$link" 2>/dev/null)" ]; then
            echo "Loading: $(readlink -f "$link")"
            model_flag="-m $link"
            break
        fi
    done
    if [ -z "$model_flag" ]; then
        echo "No active model symlink found in /models/"
    fi

    $LLAMA_SERVER --host 0.0.0.0 --port 8080 $model_flag "$@" &
    PID=$!
    echo "$PID" > $PID_FILE
    wait $PID
    rm -f $PID_FILE
}

echo "Starting llama-server..."
start_server "$@"

# Loop: when server exits (modelctl reload), restart with updated symlink
while true; do
    echo "Restarting server with updated model..."
    sleep 1
    start_server "$@"
done
