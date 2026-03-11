# Minecraft Server Scanner

A Docker-deployable application that scans the internet for Minecraft servers, stores their information in a SQLite database, and provides a web interface for browsing and filtering the results.

## Features

- **Masscan Integration**: Uses a custom [masscan fork](https://github.com/adrian154/masscan) with Minecraft protocol support
- **IP Exclusion**: Automatically excludes sensitive IP ranges (military, government, private networks) via `exclude.conf`
- **Scheduled Scanning**: Configurable scan frequency (default: once per day)
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
# Run the web server with integrated scheduler
python run.py

# Or run standalone scanner
python run_scan.py
```

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
├── run.py            # Main entry point
└── run_scan.py       # Standalone scanner
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
