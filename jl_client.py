"""John Lewis product stock client."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx

STOCK_API = "https://www.johnlewis.com/fashion-ui/api/stock/v2"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

IN_STOCK_STATUSES = frozenset(
    {
        "SKU_AVAILABLE",
        "AVAILABLE",
        "IN_STOCK",
        "LIMITED_AVAILABILITY",
        "LOW_STOCK",
    }
)

OUT_OF_STOCK_STATUSES = frozenset(
    {
        "OUT_OF_STOCK",
        "SKU_OUT_OF_STOCK",
        "UNAVAILABLE",
        "NOT_AVAILABLE",
        "NO_STOCK",
    }
)


@dataclass(frozen=True)
class StockSnapshot:
    sku: str
    available: bool
    quantity: int | None
    status: str
    message: str
    product_name: str | None = None
    product_url: str | None = None


@dataclass(frozen=True)
class ProductTarget:
    name: str
    url: str
    sku: str | None = None


class JohnLewisClient:
    def __init__(self, timeout: float = 25.0) -> None:
        self._timeout = timeout

    def _headers(self, referer: str | None = None) -> dict[str, str]:
        return {
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-GB,en;q=0.9",
            "Content-Type": "application/json",
            "Origin": "https://www.johnlewis.com",
            "Referer": referer or "https://www.johnlewis.com/",
        }

    async def fetch_page(self, url: str) -> str:
        async with httpx.AsyncClient(
            timeout=self._timeout,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT, "Accept-Language": "en-GB,en;q=0.9"},
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text

    async def resolve_skus(self, product_url: str) -> tuple[str | None, list[str]]:
        """Return (product title, sku ids) from a product or listing URL."""
        html = await self.fetch_page(product_url)
        title = _extract_title(html)
        skus = _extract_skus(html)
        return title, skus

    async def check_skus(
        self,
        skus: list[str],
        *,
        referer: str,
        product_name: str | None = None,
        product_url: str | None = None,
    ) -> list[StockSnapshot]:
        if not skus:
            return []

        api_results = await self._check_stock_api(skus, referer=referer)
        if api_results:
            return [
                StockSnapshot(
                    sku=item["sku"],
                    available=item["available"],
                    quantity=item.get("quantity"),
                    status=item["status"],
                    message=item["message"],
                    product_name=product_name,
                    product_url=product_url,
                )
                for item in api_results
            ]

        # Fallback: re-fetch product page when API is blocked or changed.
        if product_url:
            html = await self.fetch_page(product_url)
            return _snapshots_from_page_html(
                html,
                skus,
                product_name=product_name,
                product_url=product_url,
            )
        return [
            StockSnapshot(
                sku=sku,
                available=False,
                quantity=None,
                status="UNKNOWN",
                message="Could not determine stock",
                product_name=product_name,
                product_url=product_url,
            )
            for sku in skus
        ]

    async def check_product(self, target: ProductTarget) -> list[StockSnapshot]:
        referer = _normalise_product_url(target.url)
        name = target.name
        skus: list[str] = []

        if target.sku:
            skus = [target.sku.strip()]
        else:
            resolved_name, discovered = await self.resolve_skus(referer)
            if resolved_name and (not name or name.lower().startswith("pokemon")):
                name = resolved_name
            skus = discovered

        if not skus:
            raise ValueError(
                f"No SKU found for {target.url}. Open the product page in a browser, "
                "view page source, search for skuId, and set sku in config.yaml."
            )

        return await self.check_skus(
            skus,
            referer=referer,
            product_name=name,
            product_url=referer,
        )

    async def discover_search_products(
        self, search_url: str, *, max_products: int = 20
    ) -> list[ProductTarget]:
        html = await self.fetch_page(search_url)
        seen: set[str] = set()
        products: list[ProductTarget] = []

        for match in re.finditer(
            r'href="(https://www\.johnlewis\.com/[^"?#]+/p\d+)"', html
        ):
            url = _normalise_product_url(match.group(1))
            if url in seen:
                continue
            seen.add(url)
            slug = url.rsplit("/", 1)[-1]
            name = slug.replace("-", " ").title()
            products.append(ProductTarget(name=name, url=url))
            if len(products) >= max_products:
                break

        return products

    async def _check_stock_api(
        self, skus: list[str], *, referer: str
    ) -> list[dict[str, Any]] | None:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                STOCK_API,
                json={"skus": skus},
                headers=self._headers(referer=referer),
            )

        if response.status_code != 200:
            return None

        content_type = response.headers.get("content-type", "")
        if "json" not in content_type and not response.text.strip().startswith("{"):
            return None

        try:
            payload = response.json()
        except json.JSONDecodeError:
            return None

        stocks = payload.get("stocks")
        if not isinstance(stocks, list):
            return None

        parsed: list[dict[str, Any]] = []
        for entry in stocks:
            if not isinstance(entry, dict):
                continue
            sku = str(entry.get("skuId", ""))
            status = str(entry.get("availabilityStatus", "UNKNOWN"))
            quantity = entry.get("stockQuantity")
            message = str(entry.get("stockMessage") or status)
            available = _is_available(status, quantity)
            parsed.append(
                {
                    "sku": sku,
                    "available": available,
                    "quantity": int(quantity) if quantity is not None else None,
                    "status": status,
                    "message": message,
                }
            )
        return parsed or None


def _is_available(status: str, quantity: Any) -> bool:
    normalised = status.upper().replace(" ", "_")
    if normalised in OUT_OF_STOCK_STATUSES:
        return False
    if normalised in IN_STOCK_STATUSES:
        return True
    if isinstance(quantity, (int, float)) and quantity > 0:
        return True
    if isinstance(quantity, str) and quantity.isdigit() and int(quantity) > 0:
        return True
    lowered = status.lower()
    if "out of stock" in lowered or "unavailable" in lowered:
        return False
    if "in stock" in lowered or "available" in lowered:
        return True
    return False


def _normalise_product_url(url: str) -> str:
    parsed = urlparse(url.strip())
    path = parsed.path.rstrip("/")
    if not path.startswith("/"):
        path = f"/{path}"
    return f"https://www.johnlewis.com{path}"


def _extract_title(html: str) -> str | None:
    for pattern in (
        r"<title>([^<]+)</title>",
        r'"productName"\s*:\s*"([^"]+)"',
        r'"name"\s*:\s*"([^"]+)"',
    ):
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            title = match.group(1).strip()
            title = re.sub(r"\s*\|\s*John Lewis.*$", "", title, flags=re.I)
            if title:
                return title
    return None


def _extract_skus(html: str) -> list[str]:
    found: list[str] = []
    patterns = (
        r'"skuId"\s*:\s*"(\d{6,})"',
        r'"variantSkuIds"\s*:\s*\[([^\]]+)\]',
        r'data-sku(?:-id)?="(\d{6,})"',
        r'"sku"\s*:\s*"(\d{6,})"',
    )
    for pattern in patterns:
        for match in re.finditer(pattern, html):
            if match.lastindex == 1 and "," not in match.group(1):
                found.append(match.group(1))
            else:
                chunk = match.group(1)
                found.extend(re.findall(r'"(\d{6,})"', chunk))

    next_data = re.search(
        r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>',
        html,
        re.DOTALL | re.IGNORECASE,
    )
    if next_data:
        try:
            blob = json.loads(next_data.group(1))
            found.extend(_find_sku_ids(blob))
        except json.JSONDecodeError:
            pass

    deduped: list[str] = []
    seen: set[str] = set()
    for sku in found:
        if sku not in seen:
            seen.add(sku)
            deduped.append(sku)
    return deduped


def _find_sku_ids(node: Any) -> list[str]:
    results: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key in {"skuId", "sku", "variantSkuId"} and isinstance(value, (str, int)):
                text = str(value)
                if text.isdigit() and len(text) >= 6:
                    results.append(text)
            else:
                results.extend(_find_sku_ids(value))
    elif isinstance(node, list):
        for item in node:
            results.extend(_find_sku_ids(item))
    return results


def _snapshots_from_page_html(
    html: str,
    skus: list[str],
    *,
    product_name: str | None,
    product_url: str | None,
) -> list[StockSnapshot]:
    lower = html.lower()
    page_available = (
        "add to basket" in lower
        or "add to bag" in lower
        or '"instock"' in lower
        or '"in stock"' in lower
    ) and "out of stock" not in lower[:50000]

    snapshots: list[StockSnapshot] = []
    for sku in skus:
        sku_block = _html_around_sku(html, sku)
        if sku_block:
            block_lower = sku_block.lower()
            available = (
                "sku_available" in block_lower
                or "in stock" in block_lower
                or '"available":true' in block_lower.replace(" ", "")
            ) and "out of stock" not in block_lower
        else:
            available = page_available

        snapshots.append(
            StockSnapshot(
                sku=sku,
                available=available,
                quantity=None,
                status="SKU_AVAILABLE" if available else "OUT_OF_STOCK",
                message="In stock (page parse)" if available else "Out of stock (page parse)",
                product_name=product_name,
                product_url=product_url,
            )
        )
    return snapshots


def _html_around_sku(html: str, sku: str, *, radius: int = 1200) -> str | None:
    index = html.find(sku)
    if index < 0:
        return None
    start = max(0, index - radius)
    end = min(len(html), index + radius)
    return html[start:end]


def extract_product_image(html: str) -> str | None:
    """Best-effort product hero image from a John Lewis product page."""
    for pattern in (
        r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"',
        r'<meta[^>]+content="([^"]+)"[^>]+property="og:image"',
        r'"heroImage"\s*:\s*"(https://media\.johnlewiscontent\.com[^"]+)"',
        r'"(?:primary|main)Image"\s*:\s*"(https://media\.johnlewiscontent\.com[^"]+)"',
    ):
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            return match.group(1)
    return None
