"""Pokemon Center UK (en-gb) queue and availability monitor."""

from __future__ import annotations

import re
from dataclasses import dataclass

import httpx

UK_HOME = "https://www.pokemoncenter.com/en-gb"
UK_PRODUCTS = "https://www.pokemoncenter.com/en-gb/category/new-releases"

MAC_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

QUEUE_MARKERS = (
    "queue-it.net",
    "queueit",
    "Queue-it",
    "waiting room",
    "virtual queue",
    "_Incapsula_Resource",
    "queueView",
    "softblock",
    "hardblock",
    "you are in line",
    "your estimated wait",
)

OPEN_MARKERS = (
    "pokemoncenter.com/en-gb",
    "add to cart",
    "add to bag",
    "shop now",
)


@dataclass(frozen=True)
class PokemonCenterStatus:
    queue_active: bool
    status: str
    detail: str
    http_status: int | None


class PokemonCenterClient:
    def __init__(self, timeout: float = 25.0) -> None:
        self._timeout = timeout

    async def check_queue(self) -> PokemonCenterStatus:
        headers = {
            "User-Agent": MAC_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-GB,en;q=0.9",
        }
        urls = [UK_HOME, UK_PRODUCTS]
        last_status: PokemonCenterStatus | None = None

        async with httpx.AsyncClient(
            timeout=self._timeout,
            follow_redirects=True,
            headers=headers,
        ) as client:
            for url in urls:
                try:
                    response = await client.get(url)
                    body = response.text.lower()
                    final_url = str(response.url).lower()
                    last_status = _classify(response.status_code, body, final_url)
                    if last_status.queue_active:
                        return last_status
                except httpx.HTTPError as exc:
                    last_status = PokemonCenterStatus(
                        queue_active=False,
                        status="error",
                        detail=str(exc),
                        http_status=None,
                    )

        return last_status or PokemonCenterStatus(
            queue_active=False,
            status="unknown",
            detail="No response",
            http_status=None,
        )


def _classify(http_status: int, body: str, final_url: str) -> PokemonCenterStatus:
    if http_status == 403:
        return PokemonCenterStatus(
            queue_active=False,
            status="blocked",
            detail="Site returned 403 — run from your Mac/home IP",
            http_status=http_status,
        )

    for marker in QUEUE_MARKERS:
        if marker.lower() in body or marker.lower() in final_url:
            pos = _extract_queue_position(body)
            detail = f"Queue detected ({marker})"
            if pos is not None:
                detail += f" — position ~{pos:,}"
            return PokemonCenterStatus(
                queue_active=True,
                status="queue",
                detail=detail,
                http_status=http_status,
            )

    if "queue-it" in final_url:
        return PokemonCenterStatus(
            queue_active=True,
            status="queue",
            detail="Redirected to Queue-it",
            http_status=http_status,
        )

    if any(m in body for m in OPEN_MARKERS) and http_status == 200:
        return PokemonCenterStatus(
            queue_active=False,
            status="open",
            detail="Site appears open (no queue detected)",
            http_status=http_status,
        )

    return PokemonCenterStatus(
        queue_active=False,
        status="unknown",
        detail=f"HTTP {http_status} — could not confirm queue state",
        http_status=http_status,
    )


def _extract_queue_position(body: str) -> int | None:
    match = re.search(r'"pos"\s*:\s*(\d+)', body)
    if match:
        return int(match.group(1))
    match = re.search(r"position\s*[#:]?\s*(\d[\d,]*)", body, re.I)
    if match:
        return int(match.group(1).replace(",", ""))
    return None
