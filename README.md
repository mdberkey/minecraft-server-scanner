# Minecraft Server Scanner

A Docker-deployable application that scans the internet for Minecraft servers, stores their information in a SQLite database, and provides a web interface for browsing and filtering the results.

## Features

- **Masscan Integration**: Uses a custom [masscan fork](https://github.com/adrian154/masscan) with Minecraft protocol support
- **IP Exclusion**: Automatically excludes sensitive IP ranges (military, government, private networks) via `exclude.conf`
- **SQLite Database**: Stores server information including:
  - Favicon, IP, port
  - MOTD (Message of the Day)
  - Version and modded status
  - Players online, min/max ever seen
  - Country (via GeoIP)
  - Whitelist status (Yes, No, or Unknown - since the scanner only pings servers and cannot definitively determine whitelist status)
  - Date added and last updated
- **Web Interface**: Flask-based frontend with:
  - Paginated server table
  - Search functionality (IP, MOTD, Version)
  - Filtering by country, version, player count
  - Sorting by any column
  - Stats dashboard

## Running Tests

```bash
python -m unittest discover tests
```

For verbose output showing individual test results:

```bash
python -m unittest discover -v tests
```

## Quick Start

### Using Docker Compose

```bash
git clone --recurse-submodules https://github.com/yourusername/minecraft-server-scanner.git
cd minecraft-server-scanner
docker-compose up -d
```

Access the web interface at `http://localhost:5000`.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_PATH` | `/data/servers.db` | Path to SQLite database |
| `SCAN_INTERVAL_HOURS` | `24` | Hours between scans |
| `SCAN_RATE` | `20000` | Masscan rate (hosts/second) |
| `SECRET_KEY` | (random) | Flask secret key |
| `MASSCAN_PATH` | `/usr/local/bin/masscan` | Path to masscan binary |
| `EXCLUDE_FILE` | `/app/masscan/data/exclude.conf` | IP exclusion file |
| `RUN_SCAN_ON_START` | `false` | Run masscan immediately on container startup |

## Manual Installation

### Prerequisites

- Python 3.11+
- libpcap development files
- Git

### Build masscan

```bash
cd masscan
make -j$(nproc)
sudo make install
```

### Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Run the Application

```bash
# Run the web server (frontend + API)
python run.py
```

The web server runs on `http://localhost:5000`.

## Scheduled Scanning with Cron

Scans are run via cron jobs - the web server does **not** include a built-in scheduler.

1. **Run a single scan manually:**
   ```bash
   python scan_once.py
   ```

2. **Set up a cron job** (edit with `crontab -e`):
   ```bash
   # Run scan every Sunday at 3:00 AM
   0 3 * * 0 cd /path/to/minecraft-server-scanner && /usr/bin/python3 scan_once.py >> /var/log/mc-scan.log 2>&1
   ```

3. **Common cron schedules:**
   ```bash
   # Daily at 2:00 AM
   0 2 * * * ...
   
   # Every 6 hours
   0 */6 * * * ...
   
   # Every Monday at 6:00 AM
   0 6 * * 1 ...
   ```

4. **Environment variables in cron:**
   Cron has a minimal environment, so set variables explicitly:
   ```bash
   0 3 * * 0 DB_PATH=/data/servers.db MASSCAN_PATH=/usr/local/bin/masscan cd /path && python scan_once.py
   ```

5. **Architecture:**
   - **Web server** (`run.py`): Runs 24/7, serves the frontend and API
   - **Database**: SQLite file, updated by each scan
   - **Scanner** (`scan_once.py`): Run via cron, updates the database, then exits

## Project Structure

```
minecraft-server-scanner/
├── app/
│   ├── api/          # Flask API routes
│   ├── db/           # Database models
│   ├── frontend/     # Frontend utilities
│   ├── scanner/      # Scanner modules
│   └── main.py       # Flask app factory
├── masscan/          # Masscan submodule
├── templates/        # HTML templates
├── static/           # Static assets
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── run.py            # Web server entry point
├── scan_once.py      # Single scan script (for cron)
└── populate_test_data.py  # Test data generator
```

## API Endpoints

- `GET /api/servers` - List servers with pagination, search, and filters
- `GET /api/servers/<id>` - Get single server details
- `GET /api/stats` - Get aggregate statistics
- `GET /api/filters` - Get available filter options

### Query Parameters for /api/servers

| Parameter | Description |
|-----------|-------------|
| `page` | Page number (default: 1) |
| `per_page` | Items per page (default: 20) |
| `search` | Search term for IP, MOTD, version |
| `sort_by` | Column to sort by |
| `sort_order` | `asc` or `desc` |
| `country` | Filter by country |
| `version` | Filter by version |
| `min_players` | Minimum players online |
| `max_players` | Maximum players online |
| `modded_only` | Show only modded servers |
| `whitelist` | Show only servers with whitelist (Yes) |
| `no_whitelist` | Show only servers without whitelist (No) |
| `unknown_whitelist` | Show only servers with unknown whitelist status |

## License

MIT License - see LICENSE file for details.
