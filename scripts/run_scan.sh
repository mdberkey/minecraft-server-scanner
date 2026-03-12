#!/bin/bash
# Run masscan scan from host CLI
# Usage: ./scripts/run_scan.sh [rate]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DATA_DIR="$PROJECT_DIR/data"

# Ensure data directory exists
mkdir -p "$DATA_DIR"

# Default scan rate (packets per second)
RATE="${1:-20000}"

# Output file
SCAN_OUTPUT="$DATA_DIR/scan_results.ndjson"

echo "=== Minecraft Server Scanner ==="
echo "Scan rate: $RATE pps"
echo "Output: $SCAN_OUTPUT"
echo ""

# Run scan using docker container
docker run --rm \
    --cap-add=NET_RAW \
    --cap-add=NET_ADMIN \
    -v "$DATA_DIR:/data" \
    -v "$PROJECT_DIR/masscan:/app/masscan" \
    minecraft-server-scanner \
    python scan.py

echo ""
echo "Scan complete. Results saved to: $SCAN_OUTPUT"
echo "Run ./scripts/run_import.sh to import into database"
