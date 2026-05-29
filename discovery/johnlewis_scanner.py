"""Discover John Lewis product URLs with pokemon-tcg in the slug."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

from jl_client import JohnLewisClient, _extract_title, _normalise_product_url

POKEMON_TCG_SLUG = "pokemon-tcg"

PRODUCT_PATH = re.compile(
    rf"https://www\.johnlewis\.com/(?:[^/]+/)*{re.escape(POKEMON_TCG_SLUG)}[^\"'\s<>]*/p\d+",
    re.IGNORECASE,
)

RELATIVE_PRODUCT = re.compile(
    rf'href="(/[^"]*{re.escape(POKEMON_TCG_SLUG)}[^"]*/p\d+)"',
    re.IGNORECASE,
)

SEED_URLS = [
    "https://www.johnlewis.com/search?search-term=pokemon-tcg",
    "https://www.johnlewis.com/search?search-term=pokemon+tcg",
    "https://www.johnlewis.com/browse/toys/pokemon-tcg/_/N-n8a",
]


@dataclass
class DiscoveredProduct:
    url: str
    name: str
    image_url: str | None


class JohnLewisScanner:
    def __init__(self, client: JohnLewisClient | None = None) -> None:
        self._client = client or JohnLewisClient()

    async def scan(self, *, extra_seeds: list[str] | None = None) -> list[DiscoveredProduct]:
        seeds = list(SEED_URLS)
        if extra_seeds:
            seeds.extend(extra_seeds)

        found: dict[str, DiscoveredProduct] = {}
        for seed in seeds:
            try:
                html = await self._client.fetch_page(seed)
            except Exception:
                continue
            for url in _extract_pokemon_tcg_urls(html, base=seed):
                if url in found:
                    continue
                name = _name_from_url(url)
                image = _extract_og_image(html, url)
                found[url] = DiscoveredProduct(url=url, name=name, image_url=image)

        # Enrich top results with product-page metadata (cap to avoid hammering).
        enriched: list[DiscoveredProduct] = []
        for item in list(found.values())[:40]:
            try:
                html = await self._client.fetch_page(item.url)
                title = _extract_title(html) or item.name
                image = _extract_og_image(html, item.url) or item.image_url
                enriched.append(
                    DiscoveredProduct(url=item.url, name=title, image_url=image)
                )
            except Exception:
                enriched.append(item)
        enriched.extend(list(found.values())[40:])
        return enriched


def _extract_pokemon_tcg_urls(html: str, *, base: str) -> list[str]:
    urls: set[str] = set()
    for match in PRODUCT_PATH.finditer(html):
        urls.add(_normalise_product_url(match.group(0)))
    for match in RELATIVE_PRODUCT.finditer(html):
        urls.add(_normalise_product_url(urljoin(base, match.group(1))))
    # Broader fallback: any /p{id} link whose path contains pokemon-tcg
    for match in re.finditer(r'href="(https://www\.johnlewis\.com/[^"]+/p\d+)"', html):
        url = _normalise_product_url(match.group(1))
        if POKEMON_TCG_SLUG in urlparse(url).path.lower():
            urls.add(url)
    return sorted(urls)


def _name_from_url(url: str) -> str:
    path = urlparse(url).path.strip("/")
    slug = path.rsplit("/", 1)[0] if "/p" in path else path
    slug = slug.split("/")[-1]
    return slug.replace("-", " ").title()


def _extract_og_image(html: str, page_url: str) -> str | None:
    for pattern in (
        r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"',
        r'<meta[^>]+content="([^"]+)"[^>]+property="og:image"',
        r'"image"\s*:\s*"(https://media\.johnlewiscontent\.com[^"]+)"',
    ):
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            return match.group(1)
    return None
