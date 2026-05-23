import asyncio
import logging
from pathlib import Path

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger(__name__)

WWW_DIR = Path(__file__).resolve().parent.parent / 'www'


class ConnectionManager:
    def __init__(self):
        self._clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        async with self._lock:
            self._clients.add(ws)

    async def disconnect(self, ws: WebSocket):
        async with self._lock:
            self._clients.discard(ws)

    async def broadcast(self, message: str):
        async with self._lock:
            stale = []
            for ws in self._clients:
                try:
                    await ws.send_text(message)
                except Exception:
                    stale.append(ws)
            for ws in stale:
                self._clients.discard(ws)


manager = ConnectionManager()
_loop: asyncio.AbstractEventLoop | None = None


def broadcast_threadsafe(message: str) -> None:
    # Bridge from the synchronous control loop into the server's event loop.
    if _loop is None:
        return
    asyncio.run_coroutine_threadsafe(manager.broadcast(message), _loop)


def build_app() -> FastAPI:
    app = FastAPI()

    @app.websocket('/ws')
    async def websocket_endpoint(ws: WebSocket):
        await manager.connect(ws)
        try:
            while True:
                msg = await ws.receive_text()
                await manager.broadcast(msg)
        except WebSocketDisconnect:
            await manager.disconnect(ws)

    app.mount('/', StaticFiles(directory=WWW_DIR, html=True), name='static')
    return app


def run(host: str = '0.0.0.0', port: int = 8000) -> None:
    global _loop
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)
    config = uvicorn.Config(build_app(), host=host, port=port, log_level='info', loop='asyncio')
    server = uvicorn.Server(config)
    _loop.run_until_complete(server.serve())
