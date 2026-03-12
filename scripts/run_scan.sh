#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DATA_DIR="$PROJECT_DIR/data"

mkdir -p "$DATA_DIR"

RATE="${1:-20000}"
SCAN_OUTPUT="$DATA_DIR/scan_results.ndjson"

echo "=== Minecraft Server Scanner ==="
echo "Scan rate: $RATE pps"
echo "Output: $SCAN_OUTPUT"

docker run --rm \
    --cap-add=NET_RAW \
    --cap-add=NET_ADMIN \
    -v "$DATA_DIR:/data" \
    -v "$PROJECT_DIR/masscan:/app/masscan" \
    minecraft-server-scanner \
    python scan.py

echo ""
echo "Scan complete. Results: $SCAN_OUTPUT"
echo "Run ./scripts/run_import.sh to import into database"
