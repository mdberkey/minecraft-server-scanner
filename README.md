# Minecraft Server Scanner

A high-performance Minecraft server scanner that uses masscan to discover servers worldwide, stores results in SQLite, and provides a web interface for browsing and filtering.

## Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│  scan.py    │─────►│ scan_results │─────►│  import_db  │
│ (masscan)   │ NDJSON│   .ndjson    │ NDJSON│  (SQLite)  │
└─────────────┘      └──────────────┘      └──────┬──────┘
                                                   │
                                                   ▼
                                          ┌──────────────┐
                                          │  servers.db  │
                                          │   (SQLite)   │
                                          └──────┬───────┘
                                                   │
                                                   ▼
                                          ┌──────────────┐
                                          │  Flask App   │
                                          │  (run.py)    │
                                          └──────────────┘
```

## Features

- **Masscan Integration**: Uses [masscan with Minecraft support](https://github.com/adrian154/masscan)
- **NDJSON Output**: Scan results stored line-by-line for memory-efficient processing
- **Batch SQLite Imports**: Transaction-based bulk inserts for maximum performance
- **orjson Parsing**: 3-5x faster JSON processing than stdlib
- **Web Interface**: Flask-based API with pagination, search, and filtering

## Quick Start

### Using Docker Compose

```bash
git clone --recurse-submodules https://github.com/yourusername/minecraft-server-scanner.git
cd minecraft-server-scanner
docker-compose up -d
```

Access the web interface at `http://localhost:5000`.

### Manual Installation

#### Build masscan

```bash
cd masscan
make -j$(nproc)
sudo make install
```

#### Install Python Dependencies

```bash
pip install -r requirements.txt
```

## Usage

### 1. Run a Scan

```bash
python scan.py
```

This runs masscan and outputs results to `scan_results.ndjson`.

**Environment variables:**
| Variable | Default | Description |
|----------|---------|-------------|
| `MASSCAN_PATH` | `masscan/bin/masscan` | Path to masscan binary |
| `EXCLUDE_FILE` | `masscan/data/exclude.conf` | IP exclusion file |
| `SCAN_OUTPUT` | `scan_results.ndjson` | Output NDJSON file |
| `SCAN_RATE` | `20000` | Scan rate (packets/second) |

### 2. Import to Database

```bash
python import_db.py
```

This reads the NDJSON file and imports servers into SQLite.

**Environment variables:**
| Variable | Default | Description |
|----------|---------|-------------|
| `DB_PATH` | `servers.db` | SQLite database path |
| `SCAN_OUTPUT` | `scan_results.ndjson` | Input NDJSON file |
| `BATCH_SIZE` | `1000` | Records per batch |

### 3. Run the Web Server

```bash
python run.py
```

Access at `http://localhost:5000`.

**Environment variables:**
| Variable | Default | Description |
|----------|---------|-------------|
| `DB_PATH` | `servers.db` | SQLite database path |
| `SECRET_KEY` | (random) | Flask secret key |

## Scheduled Scanning with Cron

For weekly scans, use cron jobs:

```bash
# Edit crontab
crontab -e

# Run scan every Sunday at 3:00 AM
0 3 * * 0 cd /path/to/minecraft-server-scanner && python scan.py && python import_db.py >> /var/log/mc-scan.log 2>&1
```

## API Endpoints

- `GET /api/servers` - List servers with pagination, search, and filters
- `GET /api/servers/<ip>` - Get single server by IP
- `GET /api/stats` - Get aggregate statistics
- `GET /api/filters` - Get available filter options

### Query Parameters for /api/servers

| Parameter | Description |
|-----------|-------------|
| `page` | Page number (default: 1) |
| `per_page` | Items per page (default: 20) |
| `search` | Search term for IP, MOTD, version |
| `sort_by` | Column to sort by (`last_updated`, `players_online`, `version`, `ip`) |
| `sort_order` | `asc` or `desc` |
| `version` | Filter by version |
| `min_players` | Minimum players online |
| `max_players` | Maximum players online |
| `modded_only` | Show only modded servers |

## Running Tests

```bash
python -m unittest discover tests
```

For verbose output:

```bash
python -m unittest discover -v tests
```

## Project Structure

```
minecraft-server-scanner/
├── app/
│   ├── api/          # Flask API routes
│   ├── db/           # Database models
│   └── main.py       # Flask app factory
├── masscan/          # Masscan submodule
├── templates/        # HTML templates
├── static/           # Static assets
├── scan.py           # Run masscan, output NDJSON
├── import_db.py      # Import NDJSON to SQLite
├── run.py            # Web server entry point
├── requirements.txt
└── tests/
```

## Performance

For 175,000 servers:
- **Scan time**: 10-30 minutes (network-bound)
- **NDJSON parsing**: ~15-25 seconds (orjson)
- **Database import**: ~3-8 seconds (batch inserts with transactions)

## License

MIT License - see LICENSE file for details.
