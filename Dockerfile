FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    libpcap-dev \
    && rm -rf /var/lib/apt/lists/*

COPY masscan /app/masscan
WORKDIR /app/masscan
RUN make -j$(nproc)
RUN make install

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

ENV DB_PATH=/data/servers.db
ENV SCAN_INTERVAL_HOURS=24
ENV SCAN_RATE=20000
ENV MASSCAN_PATH=/usr/local/bin/masscan
ENV EXCLUDE_FILE=/app/masscan/data/exclude.conf
ENV SCAN_OUTPUT=/data/scan_results.json

RUN mkdir -p /data && chmod 777 /data

EXPOSE 5000

CMD ["python", "-m", "gunicorn", "-b", "0.0.0.0:5000", "--workers", "2", \
     "--threads", "4", "--access-logfile", "-", "--error-logfile", "-", \
     "run:app"]
