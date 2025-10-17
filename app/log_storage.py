from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Deque, Dict, List, Optional, TextIO

from .config import AppConfig

if TYPE_CHECKING:
    from .telegram_notifier import TelegramNotifier


@dataclass
class LogEntry:
    timestamp: datetime
    message: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "timestamp": self.timestamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "message": self.message,
        }


class LogStorage:
    def __init__(self, config: AppConfig, telegram_notifier: Optional[TelegramNotifier] = None):
        self._config = config
        self._buffer: Deque[LogEntry] = deque(maxlen=config.max_memory_logs)
        self._lock = asyncio.Lock()
        self._listeners: List[asyncio.Queue[LogEntry]] = []
        self._log_dir = Path(config.log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._current_log_file: Optional[Path] = None
        self._file_handle: Optional[TextIO] = None
        self._telegram_notifier = telegram_notifier

    async def add_entry(self, message: str) -> LogEntry:
        entry = LogEntry(timestamp=datetime.now(timezone.utc), message=message.rstrip("\n"))
        async with self._lock:
            self._buffer.append(entry)
            await self._notify(entry)
            if self._config.write_to_file:
                self._write_to_file(entry)
        
        # Send to Telegram if enabled
        if self._telegram_notifier:
            timestamp_str = entry.timestamp.strftime("%d/%m %H:%M:%S")
            telegram_message = f"<code>[{timestamp_str}]</code> {entry.message}"
            await self._telegram_notifier.send_message(telegram_message)
        
        return entry

    async def _notify(self, entry: LogEntry) -> None:
        for queue in list(self._listeners):
            try:
                queue.put_nowait(entry)
            except asyncio.QueueFull:
                # drop slow consumers
                continue

    async def subscribe(self, max_queue_size: int = 1000) -> asyncio.Queue[LogEntry]:
        queue: asyncio.Queue[LogEntry] = asyncio.Queue(maxsize=max_queue_size)
        async with self._lock:
            self._listeners.append(queue)
        return queue

    async def unsubscribe(self, queue: asyncio.Queue[LogEntry]) -> None:
        async with self._lock:
            if queue in self._listeners:
                self._listeners.remove(queue)

    async def get_recent(self, limit: int) -> List[Dict[str, str]]:
        async with self._lock:
            items = list(self._buffer)[-limit:]
        return [item.to_dict() for item in items]

    async def clear_buffer(self) -> None:
        async with self._lock:
            self._buffer.clear()

    def _write_to_file(self, entry: LogEntry) -> None:
        log_path = self._get_log_file_path(entry.timestamp)
        if self._current_log_file != log_path:
            self._rotate_log_file(log_path)
        if self._file_handle:
            timestamp = entry.timestamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
            self._file_handle.write(f"[{timestamp}] {entry.message}\n")
            self._file_handle.flush()

    def _get_log_file_path(self, timestamp: datetime) -> Path:
        filename = timestamp.astimezone(timezone.utc).strftime("%Y-%m-%d.log")
        return self._log_dir / filename

    def _rotate_log_file(self, new_path: Path) -> None:
        if self._file_handle:
            self._file_handle.close()
            self._file_handle = None
        self._current_log_file = new_path
        new_path.parent.mkdir(parents=True, exist_ok=True)
        self._file_handle = new_path.open("a", encoding="utf-8")

    async def close(self) -> None:
        async with self._lock:
            if self._file_handle:
                self._file_handle.close()
                self._file_handle = None

    async def cleanup_files(self) -> None:
        if not self._config.write_to_file:
            return
        if self._config.keep_days <= 0:
            return
        cutoff = datetime.now(timezone.utc).date().toordinal() - self._config.keep_days
        for file in self._log_dir.glob("*.log"):
            try:
                date_part = file.stem
                file_date = datetime.strptime(date_part, "%Y-%m-%d").date()
            except ValueError:
                continue
            if file_date.toordinal() < cutoff:
                try:
                    file.unlink(missing_ok=True)
                except OSError:
                    continue
