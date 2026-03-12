# Minecraft Server Scanner

A high-performance Minecraft server scanner that uses masscan to discover servers worldwide, stores results in SQLite, and provides a web interface for browsing and filtering.

## Features

- **Masscan Integration**: Uses [masscan with Minecraft support](https://github.com/adrian154/masscan) to scan the entire IPv4 space
- **NDJSON Output**: Scan results stored line-by-line for memory-efficient processing
- **Batch SQLite Imports**: Transaction-based bulk inserts for maximum performance
- **orjson Parsing**: 3-5x faster JSON processing than stdlib
- **Web Interface**: Flask-based API with pagination, search, and filtering

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Host Server                            │
│                                                             │
│  ┌─────────────────┐    ┌─────────────────────────────┐    │
│  │  CLI Scripts    │    │      Docker Container       │    │
│  │  (run manually) │    │                             │    │
│  │                 │    │  ┌───────────────────────┐  │    │
│  │  run_scan.sh    │───▶│  │   masscan scanner     │  │    │
│  │  run_import.sh  │───▶│  │   import_db.py        │  │    │
│  │                 │    │  │   Flask web app       │  │    │
│  │                 │    │  └───────────────────────┘  │    │
│  └─────────────────┘    └─────────────────────────────┘    │
│           │                          │                      │
│           └──────────┬───────────────┘                      │
│                      ▼                                      │
│            ┌─────────────────┐                             │
│            │  ./data/        │                             │
│            │  - servers.db   │                             │
│            │  - scan_results │                             │
│            └─────────────────┘                             │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Clone the Repository

```bash
git clone --recurse-submodules https://github.com/yourusername/minecraft-server-scanner.git
cd minecraft-server-scanner
```

### 2. Build and Start the Web App

```bash
docker compose build
docker compose up -d
```

Access the web interface at `http://localhost:5000`.

### 3. Run a Scan (from host)

```bash
./scripts/run_scan.sh
```

This scans the entire IPv4 space for Minecraft servers (port 25565). Takes 10-30 minutes depending on your network.

### 4. Import Results (from host)

```bash
./scripts/run_import.sh
```

Refresh the web interface to see the imported servers.

## Manual Installation (No Docker)

1. **Build masscan**:
   ```bash
   cd masscan
   make -j$(nproc)
   sudo make install
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run a scan**:
   ```bash
   python scan.py
   ```

4. **Import to database**:
   ```bash
   python import_db.py
   ```

5. **Start the web server**:
   ```bash
   python run.py
   ```

## Usage

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_PATH` | `servers.db` | SQLite database path |
| `SCAN_OUTPUT` | `scan_results.ndjson` | Scan output/input file |
| `MASSCAN_PATH` | `masscan/bin/masscan` | Path to masscan binary |
| `EXCLUDE_FILE` | `masscan/data/exclude.conf` | IP exclusion file |
| `SCAN_RATE` | `20000` | Scan rate (packets/second) |
| `BATCH_SIZE` | `5000` | Records per batch (import) |
| `SECRET_KEY` | (random) | Flask secret key |

### Scheduled Scanning

For automated scans, use cron:

```bash
# Edit crontab
crontab -e

# Run scan every Sunday at 3:00 AM
0 3 * * 0 cd /path/to/minecraft-server-scanner && \
    python scan.py && python import_db.py >> /var/log/mc-scan.log 2>&1
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/servers` | List servers with pagination and filters |
| `GET /api/servers/<ip>` | Get single server by IP |
| `GET /api/stats` | Get aggregate statistics |
| `GET /api/filters` | Get available filter options |

### Query Parameters for `/api/servers`

| Parameter | Description |
|-----------|-------------|
| `page` | Page number (default: 1) |
| `per_page` | Items per page (default: 20) |
| `search` | Search term for IP, MOTD, version |
| `sort_by` | Column to sort by (`last_updated`, `players_online`, `version`, `ip`) |
| `sort_order` | `asc` or `desc` |
| `version` | Filter by version string |
| `min_players` | Minimum current players |
| `max_players` | Maximum current players |
| `modded_only` | Show only modded servers (`true`/`false`) |
| `vanilla_only` | Show only vanilla servers (`true`/`false`) |
| `whitelist` | Show only whitelisted servers (`true`/`false`) |
| `no_whitelist` | Show only non-whitelisted servers (`true`/`false`) |
| `unknown_whitelist` | Show only unknown whitelist status (`true`/`false`) |

## Running Tests

```bash
python -m pytest tests/
```

## Project Structure

```
minecraft-server-scanner/
├── app/
│   ├── api/          # Flask API routes
│   ├── db/           # Database models
│   └── scanner/      # Scanner utilities
├── masscan/          # Masscan submodule
├── templates/        # HTML templates
├── static/           # Static assets
├── scripts/          # Host CLI scripts
│   ├── run_scan.sh   # Run masscan scan
│   └── run_import.sh # Import to database
├── tests/            # Unit tests
├── data/             # Database and scan output (created at runtime)
├── scan.py           # Run masscan, output NDJSON
├── import_db.py      # Import NDJSON to SQLite
├── run.py            # Web server entry point
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## Performance

For ~175,000 servers:
- **Scan time**: 10-30 minutes (network-bound)
- **NDJSON parsing**: ~15-25 seconds (orjson)
- **Database import**: ~3-8 seconds (batch inserts)

## License

MIT License - see [LICENSE](LICENSE) for details.
