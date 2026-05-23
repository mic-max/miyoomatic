import asyncio
import logging
import os
from pathlib import Path

import database
import dotenv
import notify
import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

dotenv.load_dotenv()

logger = logging.getLogger(__name__)

PC_DIR = Path(__file__).resolve().parent.parent
WWW_DIR = PC_DIR / "www"
IMG_DIR = PC_DIR / "img"
AUDIO_DIR = PC_DIR / "audio"
FONTS_DIR = PC_DIR / "fonts"


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

    async def broadcast_json(self, payload: dict):
        async with self._lock:
            stale = []
            for ws in self._clients:
                try:
                    await ws.send_json(payload)
                except Exception:
                    stale.append(ws)
            for ws in stale:
                self._clients.discard(ws)


manager = ConnectionManager()


class NotificationIn(BaseModel):
    message: str


class EncounterIn(BaseModel):
    encounter_id: str
    pokedex_id: int
    name: str
    level: int | None = None
    gender: int | None = None
    is_shiny: bool
    location_id: int
    method_id: int


def build_app() -> FastAPI:
    app = FastAPI(title="miyoomatic API")
    conn = database.connect()
    pushover_token = os.getenv("PUSHOVER_USER_TOKEN")

    @app.post("/notifications", status_code=202)
    def post_notification(n: NotificationIn):
        if not pushover_token:
            raise HTTPException(
                status_code=503, detail="PUSHOVER_USER_TOKEN not configured"
            )
        notify.send_push(pushover_token, n.message)
        return {"ok": True}

    @app.get("/spawns/{location_id}/{method_id}")
    def get_spawns(location_id: int, method_id: int):
        return database.get_spawns(conn, location_id, method_id)

    @app.get("/pokemon")
    def get_pokemon(name: str):
        pid = database.get_id_from_name(conn, name)
        if pid is None:
            raise HTTPException(status_code=404, detail=f"No pokemon named {name!r}")
        return {"pokedex_id": pid, "name": name}

    @app.post("/encounters", status_code=201)
    async def post_encounter(enc: EncounterIn):
        database.record_encounter(conn, enc.model_dump())
        await manager.broadcast_json({"type": "encounter", **enc.model_dump()})
        return {"ok": True}

    @app.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket):
        await manager.connect(ws)
        try:
            while True:
                await ws.receive_text()  # currently no client → server messages
        except WebSocketDisconnect:
            await manager.disconnect(ws)

    # More-specific mounts first; the root html mount must be last (catch-all).
    app.mount("/img", StaticFiles(directory=IMG_DIR), name="img")
    app.mount("/audio", StaticFiles(directory=AUDIO_DIR), name="audio")
    app.mount("/fonts", StaticFiles(directory=FONTS_DIR), name="fonts")
    app.mount("/", StaticFiles(directory=WWW_DIR, html=True), name="static")
    return app


app = build_app()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    uvicorn.run(app, host="0.0.0.0", port=8001, timeout_graceful_shutdown=2)
