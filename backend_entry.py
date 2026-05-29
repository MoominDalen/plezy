"""PyInstaller entrypoint — starts the bundled API server."""

from __future__ import annotations

import os
import sys
from pathlib import Path


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


def _configure_bundle_path() -> None:
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
        os.chdir(base)
        if str(base) not in sys.path:
            sys.path.insert(0, str(base))
    else:
        root = Path(__file__).resolve().parent
        os.chdir(root)
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))


def main() -> None:
    data_dir = _default_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("DATA_DIR", str(data_dir))
    os.environ.setdefault("API_HOST", "127.0.0.1")
    os.environ.setdefault("API_PORT", "8765")
    _configure_bundle_path()

    import uvicorn

    uvicorn.run(
        "api.server:app",
        host=os.environ["API_HOST"],
        port=int(os.environ["API_PORT"]),
        log_level="info",
    )


if __name__ == "__main__":
    main()
