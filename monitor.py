"""Background stock monitor with instant Telegram alerts."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Awaitable, Callable

from config_loader import load_config, load_products
from jl_client import JohnLewisClient, ProductTarget, StockSnapshot
from state_store import StateStore

logger = logging.getLogger(__name__)

NotifyFn = Callable[[int, str], Awaitable[None]]


class StockMonitor:
    def __init__(
        self,
        *,
        config_path: Path,
        state_path: Path,
        poll_interval: float,
        notify: NotifyFn,
    ) -> None:
        self._config_path = config_path
        self._state = StateStore(state_path)
        self._poll_interval = poll_interval
        self._notify = notify
        self._client = JohnLewisClient()
        self._running = False
        self._chat_ids: set[int] = set()

    def register_chat(self, chat_id: int) -> None:
        self._chat_ids.add(chat_id)

    def set_chat_ids(self, chat_ids: set[int]) -> None:
        self._chat_ids = set(chat_ids)

    async def run_loop(self) -> None:
        self._running = True
        logger.info("Stock monitor started (interval=%ss)", self._poll_interval)
        while self._running:
            try:
                await self._poll_once()
            except Exception:
                logger.exception("Monitor poll failed")
            await asyncio.sleep(self._poll_interval)

    def stop(self) -> None:
        self._running = False

    async def _poll_once(self) -> None:
        config = load_config(self._config_path)
        targets = load_products(config)

        search = config.get("search") or {}
        if isinstance(search, dict) and search.get("enabled"):
            discovered = await self._client.discover_search_products(
                str(search.get("url") or ""),
                max_products=int(search.get("max_products") or 20),
            )
            targets = _merge_targets(targets, discovered)

        if not targets:
            logger.warning("No products configured in %s", self._config_path)
            return

        for target in targets:
            try:
                snapshots = await self._client.check_product(target)
            except Exception as exc:
                logger.warning("Check failed for %s: %s", target.url, exc)
                continue

            for snapshot in snapshots:
                await self._handle_snapshot(snapshot)

        self._state.save()

    async def _handle_snapshot(self, snapshot: StockSnapshot) -> None:
        previous = self._state.was_available(snapshot.sku)
        should_alert = snapshot.available and previous is False

        self._state.update(
            snapshot.sku,
            available=snapshot.available,
            message=snapshot.message,
        )

        if not should_alert:
            return

        if not self._chat_ids:
            logger.info("Restock detected but no Telegram chat registered yet")
            return

        message = format_alert(snapshot)
        for chat_id in self._chat_ids:
            await self._notify(chat_id, message)

    async def check_now(self) -> list[StockSnapshot]:
        """Manual status check (used by /status)."""
        config = load_config(self._config_path)
        targets = load_products(config)
        all_snapshots: list[StockSnapshot] = []
        for target in targets:
            snapshots = await self._client.check_product(target)
            all_snapshots.extend(snapshots)
            for snapshot in snapshots:
                self._state.update(
                    snapshot.sku,
                    available=snapshot.available,
                    message=snapshot.message,
                )
        self._state.save()
        return all_snapshots


def format_alert(snapshot: StockSnapshot) -> str:
    title = snapshot.product_name or "Pokemon product"
    lines = [
        "🟢 IN STOCK — John Lewis",
        "",
        f"<b>{_escape_html(title)}</b>",
    ]
    if snapshot.product_url:
        lines.append(f'<a href="{snapshot.product_url}">Open on John Lewis</a>')
    lines.extend(
        [
            "",
            f"Status: {_escape_html(snapshot.message)}",
        ]
    )
    if snapshot.quantity is not None:
        lines.append(f"Quantity: {snapshot.quantity}")
    lines.append(f"SKU: {snapshot.sku}")
    return "\n".join(lines)


def format_status(snapshots: list[StockSnapshot]) -> str:
    if not snapshots:
        return "No products configured. Edit config.yaml or use /add &lt;url&gt;."

    blocks: list[str] = ["<b>John Lewis Pokemon stock</b>", ""]
    for snap in snapshots:
        icon = "🟢" if snap.available else "🔴"
        name = _escape_html(snap.product_name or snap.sku)
        blocks.append(f"{icon} {name}")
        blocks.append(f"  {_escape_html(snap.message)}")
        if snap.product_url:
            blocks.append(f'  <a href="{snap.product_url}">Product link</a>')
        blocks.append("")
    return "\n".join(blocks).strip()


def _escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _merge_targets(
    configured: list[ProductTarget], discovered: list[ProductTarget]
) -> list[ProductTarget]:
    by_url = {t.url: t for t in configured}
    for item in discovered:
        by_url.setdefault(item.url, item)
    return list(by_url.values())
