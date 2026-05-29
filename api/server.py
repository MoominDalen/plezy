"""Local HTTP + WebSocket API for the macOS UI."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from database import Database, import_yaml_products
from service import MonitorService, _product_dict

logger = logging.getLogger(__name__)

def _default_data_dir() -> Path:
    if path := os.getenv("DATA_DIR"):
        return Path(path)
    if sys.platform == "darwin":
        return (
            Path.home()
            / "Library"
            / "Application Support"
            / "StockWatch"
            / "data"
        )
    return Path("data")


DATA_DIR = _default_data_dir()
CONFIG_PATH = Path(os.getenv("CONFIG_PATH", "config.yaml"))


class ProductCreate(BaseModel):
    name: str
    url: str
    source: str = "johnlewis"
    sku: str | None = None
    image_url: str | None = None
    enabled: bool = True


class ProductUpdate(BaseModel):
    name: str | None = None
    url: str | None = None
    sku: str | None = None
    image_url: str | None = None
    enabled: bool | None = None


class SettingsUpdate(BaseModel):
    poll_interval_seconds: float | None = Field(None, ge=1, le=60)
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    telegram_enabled: bool | None = None


connections: set[WebSocket] = set()
service_holder: dict[str, MonitorService] = {}


async def _broadcast(payload: dict[str, Any]) -> None:
    dead: list[WebSocket] = []
    message = json.dumps(payload)
    for ws in connections:
        try:
            await ws.send_text(message)
        except Exception:
            dead.append(ws)
    for ws in dead:
        connections.discard(ws)


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_dotenv()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    db = Database(DATA_DIR / "stockwatch.db")
    imported = import_yaml_products(db, CONFIG_PATH)
    if imported:
        logger.info("Imported %s products from config.yaml", imported)

    poll = float(os.getenv("POLL_INTERVAL_SECONDS", db.get_setting("poll_interval", "2") or "2"))
    service = MonitorService(
        db,
        DATA_DIR / "state.json",
        poll,
        broadcast=_broadcast,
    )
    service_holder["service"] = service
    service_holder["db"] = db
    task = asyncio.create_task(service.run_loop())
    yield
    service.stop()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="StockWatch API", version="2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _db() -> Database:
    return service_holder["db"]


def _service() -> MonitorService:
    return service_holder["service"]


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/products")
async def list_products(source: str | None = None) -> list[dict]:
    return [_product_dict(r) for r in _db().list_products(source=source)]


@app.post("/products")
async def create_product(body: ProductCreate) -> dict:
    row = _db().upsert_product(
        url=body.url.strip(),
        name=body.name.strip(),
        source=body.source,
        sku=body.sku,
        image_url=body.image_url,
        enabled=body.enabled,
    )
    return _product_dict(row)


@app.put("/products/{product_id}")
async def update_product(product_id: int, body: ProductUpdate) -> dict:
    row = _db().update_product(
        product_id,
        name=body.name,
        url=body.url,
        sku=body.sku,
        image_url=body.image_url,
        enabled=body.enabled,
    )
    if not row:
        raise HTTPException(404, "Product not found")
    return _product_dict(row)


@app.delete("/products/{product_id}")
async def delete_product(product_id: int) -> dict[str, bool]:
    if not _db().delete_product(product_id):
        raise HTTPException(404, "Product not found")
    return {"ok": True}


@app.post("/products/{product_id}/check")
async def check_product(product_id: int) -> dict:
    row = await _service().check_product_by_id(product_id)
    if not row:
        raise HTTPException(404, "Product not found")
    return _product_dict(row)


@app.post("/scan/johnlewis")
async def scan_johnlewis() -> dict[str, Any]:
    rows = await _service().scan_johnlewis()
    return {"discovered": len(rows), "products": [_product_dict(r) for r in rows]}


@app.get("/pokemoncenter")
async def pokemoncenter_status() -> dict:
    return _db().get_pokemoncenter()


@app.post("/pokemoncenter/check")
async def pokemoncenter_check() -> dict:
    await _service()._poll_pokemon_center()
    return _db().get_pokemoncenter()


@app.get("/settings")
async def get_settings() -> dict[str, str]:
    settings = _db().all_settings()
    settings.setdefault("poll_interval_seconds", os.getenv("POLL_INTERVAL_SECONDS", "2"))
    return settings


@app.put("/settings")
async def put_settings(body: SettingsUpdate) -> dict[str, str]:
    db = _db()
    if body.poll_interval_seconds is not None:
        db.set_setting("poll_interval", str(body.poll_interval_seconds))
        _service()._poll_interval = body.poll_interval_seconds
    if body.telegram_bot_token is not None:
        db.set_setting("telegram_bot_token", body.telegram_bot_token)
    if body.telegram_chat_id is not None:
        db.set_setting("telegram_chat_id", body.telegram_chat_id)
    if body.telegram_enabled is not None:
        db.set_setting("telegram_enabled", "1" if body.telegram_enabled else "0")
    return await get_settings()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    connections.add(websocket)
    try:
        await websocket.send_json({"type": "connected"})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        connections.discard(websocket)


def main() -> None:
    import uvicorn

    logging.basicConfig(level=logging.INFO)
    host = os.getenv("API_HOST", "127.0.0.1")
    port = int(os.getenv("API_PORT", "8765"))
    uvicorn.run("api.server:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
