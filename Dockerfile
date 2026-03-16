FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for masscan
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    libpcap-dev \
    && rm -rf /var/lib/apt/lists/*

# Build and install masscan
COPY masscan /app/masscan
WORKDIR /app/masscan
RUN make -j$(nproc) && make install

# Set up Python application
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r requirements.txt

# Create data directory
RUN mkdir -p /data

# Default environment variables
ENV DB_PATH=/data/servers.db
ENV SCAN_OUTPUT=/data/scan_results.ndjson
ENV MASSCAN_PATH=/usr/bin/masscan
ENV EXCLUDE_FILE=/app/masscan/data/exclude.conf

EXPOSE 5000

# Default command runs the web application
CMD ["python", "-m", "gunicorn", "-b", "0.0.0.0:5000", "--workers", "2", \
     "--threads", "4", "--access-logfile", "-", "--error-logfile", "-", \
     "run:app"]
