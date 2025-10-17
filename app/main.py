from __future__ import annotations

import asyncio
import contextlib
from typing import AsyncIterator

from fastapi import Depends, FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from .config import AppConfig, get_config
from .log_storage import LogStorage
from .telegram_notifier import TelegramNotifier
from .udp_listener import start_udp_server


CONFIG = get_config()


async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    config = CONFIG
    
    # Initialize Telegram notifier
    telegram_notifier = TelegramNotifier(config)
    await telegram_notifier.start()
    
    # Initialize storage with Telegram notifier
    storage = LogStorage(config, telegram_notifier)

    app.state.config = config
    app.state.storage = storage
    app.state.telegram_notifier = telegram_notifier

    transport = await start_udp_server(config, storage)

    cleanup_task = None
    if config.keep_days > 0:
        cleanup_task = asyncio.create_task(_cleanup_worker(storage, config.keep_days))

    try:
        yield
    finally:
        if cleanup_task:
            cleanup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await cleanup_task
        transport.close()
        await telegram_notifier.stop()
        await storage.close()
        await asyncio.sleep(0)


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CONFIG.allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _cleanup_worker(storage: LogStorage, keep_days: int) -> None:
    if keep_days <= 0:
        return
    while True:
        await asyncio.sleep(3600)
        await storage.cleanup_files()


async def get_storage() -> LogStorage:
    return app.state.storage


async def get_config_dependency() -> AppConfig:
    return app.state.config


@app.get("/logs")
async def read_logs(limit: int = Query(500, ge=1, le=5000), storage: LogStorage = Depends(get_storage)) -> JSONResponse:
    logs = await storage.get_recent(limit)
    return JSONResponse(content={"logs": logs})


@app.delete("/logs")
async def clear_logs(storage: LogStorage = Depends(get_storage)) -> JSONResponse:
    await storage.clear_buffer()
    return JSONResponse(content={"status": "ok", "message": "Buffer cleared"})


@app.websocket("/ws")
async def websocket_logs(
    websocket: WebSocket, config: AppConfig = Depends(get_config_dependency), storage: LogStorage = Depends(get_storage)
) -> None:
    token = websocket.query_params.get("token")
    if config.websocket_token and token != config.websocket_token:
        await websocket.close(code=4401)
        return

    await websocket.accept()
    queue = await storage.subscribe()
    try:
        while True:
            entry = await queue.get()
            await websocket.send_json(entry.to_dict())
    except WebSocketDisconnect:
        pass
    finally:
        await storage.unsubscribe(queue)


@app.get("/")
async def index() -> FileResponse:
    return FileResponse("app/static/index.html")
