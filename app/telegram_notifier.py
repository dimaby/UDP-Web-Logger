from __future__ import annotations

import asyncio
import logging
from typing import Optional

import httpx

from .config import AppConfig

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Telegram bot notifier for sending log messages"""

    def __init__(self, config: AppConfig):
        self._config = config
        self._enabled = config.telegram_enabled
        self._bot_token = config.telegram_bot_token
        self._chat_id = config.telegram_chat_id
        self._client: Optional[httpx.AsyncClient] = None
        self._queue: asyncio.Queue[str] = asyncio.Queue(maxsize=100)
        self._worker_task: Optional[asyncio.Task] = None

        if self._enabled and not self._bot_token:
            logger.warning("Telegram is enabled but bot token is not configured")
            self._enabled = False

        if self._enabled and not self._chat_id:
            logger.warning("Telegram is enabled but chat ID is not configured")
            self._enabled = False

    async def start(self) -> None:
        """Start the Telegram notifier worker"""
        if not self._enabled:
            logger.info("Telegram notifier is disabled")
            return

        self._client = httpx.AsyncClient(timeout=10.0)
        self._worker_task = asyncio.create_task(self._worker())
        logger.info(f"Telegram notifier started for chat ID: {self._chat_id}")

    async def stop(self) -> None:
        """Stop the Telegram notifier worker"""
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

        if self._client:
            await self._client.aclose()
            self._client = None

    async def send_message(self, message: str) -> None:
        """Queue a message to be sent to Telegram"""
        if not self._enabled:
            return

        try:
            self._queue.put_nowait(message)
        except asyncio.QueueFull:
            logger.warning("Telegram queue is full, dropping message")

    async def _worker(self) -> None:
        """Background worker that sends messages from the queue"""
        while True:
            try:
                message = await self._queue.get()
                await self._send_to_telegram(message)
                # Rate limiting: wait a bit between messages
                await asyncio.sleep(0.5)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in Telegram worker: {e}")
                await asyncio.sleep(1)

    async def _send_to_telegram(self, message: str) -> None:
        """Send a message to Telegram via Bot API"""
        if not self._client:
            return

        url = f"https://api.telegram.org/bot{self._bot_token}/sendMessage"
        
        # Truncate message if too long (Telegram limit is 4096 characters)
        if len(message) > 4000:
            message = message[:3997] + "..."

        payload = {
            "chat_id": self._chat_id,
            "text": message,
            "parse_mode": "HTML",
        }

        try:
            response = await self._client.post(url, json=payload)
            response.raise_for_status()
            logger.debug(f"Message sent to Telegram: {message[:50]}...")
        except httpx.HTTPError as e:
            logger.error(f"Failed to send message to Telegram: {e}")
        except Exception as e:
            logger.error(f"Unexpected error sending to Telegram: {e}")
