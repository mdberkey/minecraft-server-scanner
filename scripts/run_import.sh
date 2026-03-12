#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DATA_DIR="$PROJECT_DIR/data"

SCAN_INPUT="$DATA_DIR/scan_results.ndjson"
DB_PATH="$DATA_DIR/servers.db"

echo "=== Minecraft Server Scanner ==="
echo "Importing scan results into database..."
echo "Input: $SCAN_INPUT"
echo "Database: $DB_PATH"

if [ ! -f "$SCAN_INPUT" ]; then
    echo "Error: Scan results not found at $SCAN_INPUT"
    echo "Run ./scripts/run_scan.sh first to create scan results."
    exit 1
fi

docker run --rm \
    -v "$DATA_DIR:/data" \
    minecraft-server-scanner \
    python import_db.py

echo ""
echo "Import complete. Database: $DB_PATH"
echo "Start the web UI with: docker compose up -d"
