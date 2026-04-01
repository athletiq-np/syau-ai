#!/bin/bash
# Start ComfyUI on the GPU server as a background service.
# Run this before starting docker-compose.worker.yml.
# Logs go to /data/ComfyUI/comfyui.log

COMFYUI_DIR="/data/ComfyUI"
PYTHON="$COMFYUI_DIR/venv/bin/python"
LOG="$COMFYUI_DIR/comfyui.log"
PID_FILE="/tmp/comfyui.pid"

if [ -f "$PID_FILE" ] && kill -0 "$(cat $PID_FILE)" 2>/dev/null; then
    echo "ComfyUI already running (PID $(cat $PID_FILE))"
    exit 0
fi

echo "Starting ComfyUI..."
cd "$COMFYUI_DIR"
nohup "$PYTHON" main.py \
    --listen 0.0.0.0 \
    --port 8188 \
    --disable-auto-launch \
    --output-directory "$COMFYUI_DIR/output" \
    >> "$LOG" 2>&1 &

echo $! > "$PID_FILE"
echo "ComfyUI started (PID $!), log: $LOG"
echo "Waiting for ComfyUI to be ready..."

for i in $(seq 1 30); do
    if curl -s http://localhost:8188/system_stats > /dev/null 2>&1; then
        echo "ComfyUI is ready."
        exit 0
    fi
    sleep 2
done

echo "ERROR: ComfyUI did not start within 60 seconds. Check $LOG"
exit 1
