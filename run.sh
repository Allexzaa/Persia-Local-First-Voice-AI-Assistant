#!/usr/bin/env bash
# Launch Persia — sets Python venv and library paths explicitly.
# Works regardless of whether the venv was activated in the current shell.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/voice-agent/.venv"
PYTHON="$VENV/bin/python3"

if [ ! -f "$PYTHON" ]; then
    echo "[run.sh] ERROR: venv not found at $VENV"
    echo "         Run: cd voice-agent && python3 -m venv .venv && pip install -r requirements.txt"
    exit 1
fi

# Kill any stale UI server (8766) — but leave the browser bridge (8765) running
# so the Chrome extension stays connected across Persia restarts.
for PORT in 8766; do
    PID=$(fuser "${PORT}/tcp" 2>/dev/null | tr -d ' ')
    if [ -n "$PID" ]; then
        echo "[run.sh] Port ${PORT} in use by PID ${PID} — killing stale process"
        kill "$PID" 2>/dev/null || true
        sleep 0.5
    fi
done

# Start browser bridge as a persistent background process if not already running
if ! curl -s http://127.0.0.1:8765/health > /dev/null 2>&1; then
    echo "[run.sh] Starting browser bridge on port 8765..."
    nohup "$PYTHON" "$SCRIPT_DIR/browser-bridge/server.py" > /tmp/persia-bridge.log 2>&1 &
    # Wait up to 3 seconds for it to bind
    for i in $(seq 1 30); do
        if curl -s http://127.0.0.1:8765/health > /dev/null 2>&1; then
            echo "[run.sh] Browser bridge ready"
            break
        fi
        sleep 0.1
    done
else
    echo "[run.sh] Browser bridge already running on port 8765"
fi

export VIRTUAL_ENV="$VENV"
export LD_LIBRARY_PATH="$VENV/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

cd "$SCRIPT_DIR/voice-agent"
exec "$PYTHON" main.py "$@"
