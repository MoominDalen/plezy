"""Background monitoring service used by API and Telegram bot."""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Awaitable, Callable

from database import Database, ProductRow
from discovery.johnlewis_scanner import JohnLewisScanner
from jl_client import JohnLewisClient, ProductTarget, extract_product_image
from pc_client import PokemonCenterClient
from state_store import StateStore

logger = logging.getLogger(__name__)

BroadcastFn = Callable[[dict], Awaitable[None]]
NotifyFn = Callable[[int, str], Awaitable[None]]


class MonitorService:
    def __init__(
        self,
        db: Database,
        state_path: Path,
        poll_interval: float,
        *,
        notify: NotifyFn | None = None,
        broadcast: BroadcastFn | None = None,
    ) -> None:
        self._db = db
        self._state = StateStore(state_path)
        self._poll_interval = poll_interval
        self._notify = notify
        self._broadcast = broadcast
        self._jl = JohnLewisClient()
        self._pc = PokemonCenterClient()
        self._scanner = JohnLewisScanner(self._jl)
        self._running = False
        self._chat_ids: set[int] = set()

    def register_chat(self, chat_id: int) -> None:
        self._chat_ids.add(chat_id)

    def set_chat_ids(self, chat_ids: set[int]) -> None:
        self._chat_ids = set(chat_ids)

    async def run_loop(self) -> None:
        self._running = True
        logger.info("Monitor service started (interval=%ss)", self._poll_interval)
        while self._running:
            try:
                await self.poll_all()
            except Exception:
                logger.exception("Poll cycle failed")
            await asyncio.sleep(self._poll_interval)

    def stop(self) -> None:
        self._running = False

    async def poll_all(self) -> None:
        await self._poll_john_lewis()
        await self._poll_pokemon_center()
        await self._emit({"type": "tick"})

    async def scan_johnlewis(self) -> list[ProductRow]:
        discovered = await self._scanner.scan()
        added: list[ProductRow] = []
        for item in discovered:
            row = self._db.upsert_product(
                url=item.url,
                name=item.name,
                source="johnlewis",
                image_url=item.image_url,
            )
            added.append(row)
        await self._emit({"type": "scan_complete", "count": len(added)})
        return added

    async def check_product_by_id(self, product_id: int) -> ProductRow | None:
        row = self._db.get_product(product_id)
        if not row or not row.enabled:
            return row
        if row.source == "johnlewis":
            await self._check_jl_row(row)
        return self._db.get_product(product_id)

    async def _poll_john_lewis(self) -> None:
        for row in self._db.list_products(source="johnlewis"):
            if not row.enabled:
                continue
            try:
                await self._check_jl_row(row)
            except Exception as exc:
                logger.warning("JL check failed %s: %s", row.url, exc)

    async def _check_jl_row(self, row: ProductRow) -> None:
        target = ProductTarget(name=row.name, url=row.url, sku=row.sku)
        snapshots = await self._jl.check_product(target)
        if not snapshots:
            return

        snapshot = snapshots[0]
        previous = self._state.was_available(snapshot.sku)
        should_alert = snapshot.available and previous is False

        self._state.update(
            snapshot.sku,
            available=snapshot.available,
            message=snapshot.message,
        )
        self._state.save()

        self._db.update_stock(
            row.id,
            available=snapshot.available,
            status_message=snapshot.message,
        )

        if not row.image_url:
            try:
                html = await self._jl.fetch_page(row.url)
                image = extract_product_image(html)
                if image:
                    self._db.update_product(row.id, image_url=image)
            except Exception:
                pass

        updated = self._db.get_product(row.id)
        if updated:
            await self._emit({"type": "product_updated", "product": _product_dict(updated)})

        if should_alert and self._notify and self._chat_ids:
            message = _format_alert(updated or row, snapshot)
            for chat_id in self._chat_ids:
                await self._notify(chat_id, message)

    async def _poll_pokemon_center(self) -> None:
        status = await self._pc.check_queue()
        previous_active = self._db.get_pokemoncenter().get("queue_active", 0)
        self._db.update_pokemoncenter(
            queue_active=status.queue_active,
            status=status.status,
            detail=status.detail,
        )
        payload = {
            "type": "pokemoncenter_updated",
            "queue_active": status.queue_active,
            "status": status.status,
            "detail": status.detail,
        }
        await self._emit(payload)

        if status.queue_active and not previous_active and self._notify and self._chat_ids:
            text = (
                "🟠 <b>Pokemon Center UK — queue active</b>\n\n"
                f"{status.detail}\n"
                f'<a href="https://www.pokemoncenter.com/en-gb">Open Pokemon Center UK</a>'
            )
            for chat_id in self._chat_ids:
                await self._notify(chat_id, text)

    async def _emit(self, payload: dict) -> None:
        if self._broadcast:
            await self._broadcast(payload)


def _product_dict(row: ProductRow) -> dict:
    return {
        "id": row.id,
        "source": row.source,
        "name": row.name,
        "url": row.url,
        "sku": row.sku,
        "image_url": row.image_url,
        "enabled": row.enabled,
        "available": row.available,
        "status_message": row.status_message,
        "last_checked": row.last_checked,
    }


def _format_alert(row: ProductRow, snapshot) -> str:
    title = row.name
    lines = [
        "🟢 <b>IN STOCK — John Lewis</b>",
        "",
        f"<b>{title}</b>",
        f'<a href="{row.url}">Open product</a>',
        "",
        f"Status: {snapshot.message}",
    ]
    if snapshot.quantity is not None:
        lines.append(f"Qty: {snapshot.quantity}")
    return "\n".join(lines)


def build_service(data_dir: Path) -> MonitorService:
    db_path = data_dir / "stockwatch.db"
    state_path = data_dir / "state.json"
    db = Database(db_path)
    poll = float(os.getenv("POLL_INTERVAL_SECONDS", "2"))
    return MonitorService(db, state_path, poll)
