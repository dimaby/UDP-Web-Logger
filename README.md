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

```bash
docker build -t smart-udp-log-viewer .
docker run -d \ 
  -p 5140:5140/udp \ 
  -p 8080:8080 \ 
  -v /var/log/smartlog:/logs \ 
  smart-udp-log-viewer:latest
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
