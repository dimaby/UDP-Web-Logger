# Smart UDP Log Viewer

A lightweight FastAPI-based service that listens for UDP log messages and streams them to a web UI in real time.

## Features

- Async UDP listener with configurable whitelist
- In-memory ring buffer for the most recent messages
- Optional daily log files with automatic cleanup
- FastAPI HTTP API for retrieving recent logs
- WebSocket streaming endpoint for live updates
- Responsive, zero-dependency web UI with pause/resume, search, auto-scroll, clear, and download controls

## Configuration

Configuration is provided through `config.json` (defaults shown below):

```json
{
  "udp_port": 5140,
  "web_port": 8080,
  "max_memory_logs": 10000,
  "log_dir": "./logs",
  "keep_days": 3,
  "allowed_origins": ["*"],
  "write_to_file": true,
  "udp_whitelist": [],
  "websocket_token": null
}
```

- `write_to_file`: Enable or disable daily log file persistence.
- `udp_whitelist`: Restrict UDP ingestion to specific IP addresses (empty list allows all sources).
- `websocket_token`: Optional token required as `ws://host/ws?token=...`.

## Running locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

The FastAPI app starts the UDP listener automatically using the configured port.

## Docker

### Build and run manually

```bash
docker build -t smart-udp-log-viewer .
docker run -d \ 
  -p 5140:5140/udp \ 
  -p 8080:8080 \ 
  -v /var/log/smartlog:/logs \ 
  smart-udp-log-viewer:latest
```

### Using Docker Compose (recommended)

```bash
docker compose up -d --build
```

View logs:
```bash
docker compose logs -f
```

Stop:
```bash
docker compose down
```

## API

- `GET /logs?limit=500` — Fetch the most recent log entries (up to 5000).
- `GET /` — Static HTML UI.
- `WS /ws` — WebSocket stream of log entries in JSON format:

```json
{
  "timestamp": "2025-10-17T12:34:56Z",
  "message": "Temperature sensor: 24.6°C"
}
```

## Frontend shortcuts

- **Pause / Resume** — Temporarily halt live updates while continuing to buffer messages.
- **Search** — Case-insensitive filtering of the current view.
- **Auto-scroll** — Toggle following the latest entry.
- **Clear** — Reset the displayed buffer.
- **Save log** — Download the current buffer as a text file.

---

## 🚀 Production Deployment (Ubuntu Server)

### Prerequisites

- Ubuntu 20.04+ server with root access
- Open ports: 5140/udp, 8080/tcp

### Installation Steps

1. **Update system and install dependencies**

```bash
apt update && apt upgrade -y
apt install -y ca-certificates curl gnupg git
```

2. **Install Docker**

```bash
# Add Docker's official GPG key
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

# Add Docker repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

3. **Clone the repository**

```bash
cd /opt
git clone https://github.com/dimaby/UDP-Web-Logger.git udp-logger
cd udp-logger
```

4. **Start the service**

```bash
docker compose up -d --build
```

5. **Verify the service is running**

```bash
docker compose ps
docker compose logs -f
```

6. **Setup systemd service for auto-start on boot**

```bash
cat > /etc/systemd/system/udp-logger.service << 'EOF'
[Unit]
Description=Smart UDP Log Viewer
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/udp-logger
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable udp-logger.service
systemctl start udp-logger.service
```

7. **Check service status**

```bash
systemctl status udp-logger.service
docker ps
```

### Access the Web UI

Open your browser and navigate to:
```
http://YOUR_SERVER_IP:8080
```

---

## 🧪 Testing with socat

### Install socat

**macOS:**
```bash
brew install socat
```

**Ubuntu/Debian:**
```bash
apt install -y socat
```

### Send test UDP messages

```bash
# Single message
echo "ESP32-01 booting..." | socat - UDP:YOUR_SERVER_IP:5140

# Multiple messages
echo "Connected to WiFi SSID: my_home_net" | socat - UDP:YOUR_SERVER_IP:5140
echo "Temperature sensor: 24.6°C" | socat - UDP:YOUR_SERVER_IP:5140
echo "Humidity: 65%" | socat - UDP:YOUR_SERVER_IP:5140
echo "Battery voltage: 3.7V" | socat - UDP:YOUR_SERVER_IP:5140
```

### Send messages in a loop (stress test)

```bash
for i in {1..100}; do
  echo "Test message #$i - $(date +%H:%M:%S)" | socat - UDP:YOUR_SERVER_IP:5140
  sleep 0.1
done
```

### Send multiline logs

```bash
cat << 'EOF' | socat - UDP:YOUR_SERVER_IP:5140
System startup complete
Memory: 512KB free
CPU: 80MHz
Network: Connected
EOF
```

---

## 📝 Maintenance Commands

### Update from GitHub

```bash
cd /opt/udp-logger
git pull
docker compose up -d --build
```

### View logs

```bash
docker compose logs -f
```

### Restart service

```bash
docker compose restart
```

### Stop service

```bash
docker compose down
```

### Check disk usage

```bash
du -sh /opt/udp-logger/logs
```

### Clean old log files manually

```bash
find /opt/udp-logger/logs -name "*.log" -mtime +3 -delete
```
