"""Load watchlist from YAML and environment."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from jl_client import ProductTarget


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        example = path.parent / "config.yaml.example"
        raise FileNotFoundError(
            f"Missing {path}. Copy {example} to {path} and add your product URLs."
        )
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data


def load_products(config: dict[str, Any]) -> list[ProductTarget]:
    products: list[ProductTarget] = []
    for entry in config.get("products") or []:
        if not isinstance(entry, dict):
            continue
        url = str(entry.get("url", "")).strip()
        if not url:
            continue
        sku = str(entry.get("sku") or "").strip() or None
        name = str(entry.get("name") or "John Lewis product").strip()
        products.append(ProductTarget(name=name, url=url, sku=sku))
    return products


def env_poll_interval(default: float = 2.0) -> float:
    raw = os.getenv("POLL_INTERVAL_SECONDS", str(default))
    try:
        value = float(raw)
    except ValueError:
        value = default
    return max(1.0, min(value, 60.0))
