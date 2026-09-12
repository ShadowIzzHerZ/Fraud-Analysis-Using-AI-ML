#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"

echo "=== ZenPay Cloud Sync Tunnel Launcher ==="

# Check/start Python backend
if ! lsof -i :8080 >/dev/null 2>&1; then
    echo "Starting Python backend (main.py) in background..."
    nohup .venv/bin/python main.py > .main.log 2>&1 &
    sleep 2
else
    echo "Python backend is already running on port 8080."
fi

# Ensure cloudflared is installed
if ! command -v cloudflared >/dev/null 2>&1; then
    echo "cloudflared not found. Installing via brew..."
    brew install cloudflared
fi

echo "Starting Cloudflare quick tunnel to http://localhost:8080..."
LOGFILE="/tmp/zenpay_tunnel.log"
rm -f "$LOGFILE"

nohup cloudflared tunnel --url http://localhost:8080 > "$LOGFILE" 2>&1 &
TUNNEL_PID=$!
echo "Tunnel PID: $TUNNEL_PID"

echo "Waiting for public HTTPS tunnel URL..."
TUNNEL_URL=""
for i in {1..30}; do
    if grep -q "trycloudflare.com" "$LOGFILE" 2>/dev/null; then
        TUNNEL_URL=$(grep -o 'https://[-a-zA-Z0-9]*\.trycloudflare\.com' "$LOGFILE" | head -n 1)
        if [ -n "$TUNNEL_URL" ]; then
            break
        fi
    fi
    sleep 1
done

if [ -n "$TUNNEL_URL" ]; then
    echo "==========================================================="
    echo "Public Cloud Sync URL: $TUNNEL_URL"
    echo "==========================================================="
    echo "$TUNNEL_URL" > "$DIR/cloud_url.txt"
    echo "Saved to $DIR/cloud_url.txt"
    echo "ZenPay devices anywhere in the world (4G/5G or any Wi-Fi)"
    echo "can now perform P2P transfers using this endpoint!"
else
    echo "Failed to retrieve public tunnel URL. Check $LOGFILE"
fi
