# Minecraft Server Scanner

A high-performance Minecraft server scanner that uses masscan to discover servers worldwide, stores results in SQLite, and provides a web interface for browsing and filtering.

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
| `BATCH_SIZE` | `1000` | Records per batch (import) |
| `SECRET_KEY` | (random) | Flask secret key |

### Scheduled Scanning

For automated scans, use cron:

```bash
# Edit crontab
crontab -e

# Run scan every Sunday at 3:00 AM
0 3 * * 0 cd /path/to/minecraft-server-scanner && python scan.py && python import_db.py >> /var/log/mc-scan.log 2>&1
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
| `sort_by` | Column to sort by |
| `sort_order` | `asc` or `desc` |
| `version` | Filter by version |
| `max_players` | Maximum players online |
| `modded_only` | Show only modded servers |

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
│   ├── frontend/     # Frontend routes
│   └── scanner/      # Scanner utilities
├── masscan/          # Masscan submodule
├── templates/        # HTML templates
├── static/           # Static assets
├── tests/            # Unit tests
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
