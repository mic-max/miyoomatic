import argparse
import asyncio
import logging
import os
import random
import secrets
import uuid
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

# New random id every time the process starts. Page compares against the previous one
# it has seen and reloads itself when this changes — i.e. after the API restarts.
SESSION_ID = secrets.token_hex(8)


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
    pushover_user = os.getenv("PUSHOVER_USER_TOKEN")
    pushover_app = os.getenv("PUSHOVER_API_TOKEN")

    def pushover_ready() -> bool:
        return bool(pushover_user and pushover_app)

    @app.post("/notifications", status_code=202)
    def post_notification(n: NotificationIn):
        if not pushover_ready():
            raise HTTPException(
                status_code=503,
                detail="PUSHOVER_USER_TOKEN and/or PUSHOVER_API_TOKEN not configured",
            )
        notify.send_push(pushover_app, pushover_user, n.message)
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

    async def _persist_encounter(enc: EncounterIn) -> dict:
        database.record_encounter(conn, enc.model_dump())
        await manager.broadcast_json({"type": "encounter", **enc.model_dump()})
        if enc.is_shiny and pushover_ready():
            lvl = f"Lv{enc.level} " if enc.level is not None else ""
            notify.send_push(
                pushover_app,
                pushover_user,
                message=f"{lvl}{enc.name} (#{enc.pokedex_id:03d})",
                title=f"✨ Shiny {enc.name}!",
            )
        return {"ok": True, "encounter_id": enc.encounter_id}

    @app.post("/encounters", status_code=201)
    async def post_encounter(enc: EncounterIn):
        return await _persist_encounter(enc)

    @app.post("/encounters/random/{location_id}/{method_id}", status_code=201)
    async def post_random_encounter(
        location_id: int, method_id: int, shiny_odds: int = 8192
    ):
        # Test endpoint: weighted-pick a spawn for the location/method, then persist+broadcast
        # exactly like POST /encounters. The page sees the result via the WS broadcast.
        spawns = database.get_spawns(conn, location_id, method_id)
        flat = []
        for pid, p in spawns.items():
            for row in p["levels"]:
                flat.append(
                    {
                        "pokedex_id": pid,
                        "name": p["name"],
                        "level": row["level"],
                        "odds": row["odds"],
                    }
                )
        if not flat:
            raise HTTPException(
                status_code=404,
                detail=f"No spawns for location {location_id} method {method_id}",
            )
        total = sum(x["odds"] for x in flat)
        assert total == 256
        r = random.random() * total
        pick = flat[-1]
        for row in flat:
            r -= row["odds"]
            if r <= 0:
                pick = row
                break
        # Gender enum: MALE=2, FEMALE=3 (Pokemon.Gender in pc/src/Pokemon.py).
        gender = random.choice([2, 3])
        is_shiny = shiny_odds > 0 and random.randint(1, shiny_odds) == 1
        enc = EncounterIn(
            encounter_id=str(uuid.uuid7()),
            pokedex_id=pick["pokedex_id"],
            name=pick["name"],
            level=pick["level"],
            gender=gender,
            is_shiny=is_shiny,
            location_id=location_id,
            method_id=method_id,
        )
        return await _persist_encounter(enc)

    @app.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket):
        await manager.connect(ws)
        try:
            await ws.send_json({"type": "hello", "session_id": SESSION_ID})
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
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Restart the server on Python/HTML/JS/CSS changes (dev only).",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    if args.reload:
        uvicorn.run(
            "api:app",
            host="0.0.0.0",
            port=8001,
            timeout_graceful_shutdown=2,
            reload=True,
            reload_dirs=[str(PC_DIR / "src"), str(PC_DIR / "www")],
            reload_includes=["*.py", "*.html", "*.js", "*.css"],
        )
    else:
        uvicorn.run(app, host="0.0.0.0", port=8001, timeout_graceful_shutdown=2)
