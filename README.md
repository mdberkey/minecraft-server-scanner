# Minecraft Server Scanner

A high-performance Minecraft server scanner that uses masscan to discover servers worldwide, stores results in SQLite, and provides a web interface for browsing and filtering.

## Features

- **Masscan Integration**: Uses a [fork of masscan with Minecraft support](https://github.com/adrian154/masscan) to scan the entire IPv4 space.
- **Database Importing**: Extracts sever info (IP, MOTD, Version, etc.) and stores im a SQLite database.
- **Web Interface**: Flask-based API with pagination, search, and filtering.

## Architecture

## Quick Start

### 1. Clone the Repository

```bash
git clone --recurse-submodules git@github.com:mdberkey/minecraft-server-scanner.git
```

### 2. Build and Start the Web App

```bash
docker compose build
docker compose up -d
```


### 3. Run a Scan (from host)

```bash
./scripts/run_scan.sh
```


### 4. Import Results (from host)

```bash
./scripts/run_import.sh
```


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
| `sort_by` | Column to sort by (`last_updated`, `players_online`, `version`, `ip`, `date_added`) |
| `sort_order` | `asc` or `desc` |
| `version` | Filter by version string |
| `current_players` | Minimum current players |
| `max_players` | Minimum max player capacity |
| `modded_only` | Show only modded servers (`true`/`false`) |
| `vanilla_only` | Show only vanilla servers (`true`/`false`) |
| `whitelist` | Show only whitelisted servers (`true`) |
| `no_whitelist` | Show only non-whitelisted servers (`true`) |
| `unknown_whitelist` | Show only unknown whitelist status (`true`) |

## Tests

Run all tests with pytest:
```bash
python -m pytest tests/
```
