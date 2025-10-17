from __future__ import annotations

import asyncio
from typing import Optional

from .config import AppConfig
from .log_storage import LogStorage


class UDPServerProtocol(asyncio.DatagramProtocol):
    def __init__(self, config: AppConfig, storage: LogStorage):
        self.config = config
        self.storage = storage
        self.transport: Optional[asyncio.transports.DatagramTransport] = None

    def connection_made(self, transport: asyncio.transports.DatagramTransport) -> None:
        self.transport = transport

    def datagram_received(self, data: bytes, addr) -> None:  # type: ignore[override]
        host, _ = addr
        if self.config.udp_whitelist and host not in self.config.udp_whitelist:
            return
        message = data.decode("utf-8", errors="replace")
        lines = message.splitlines() or [message]
        for line in lines:
            if not line:
                continue
            asyncio.create_task(self.storage.add_entry(line))


async def start_udp_server(config: AppConfig, storage: LogStorage) -> asyncio.transports.DatagramTransport:
    loop = asyncio.get_running_loop()
    transport, _ = await loop.create_datagram_endpoint(
        lambda: UDPServerProtocol(config, storage), local_addr=("0.0.0.0", config.udp_port)
    )
    return transport
