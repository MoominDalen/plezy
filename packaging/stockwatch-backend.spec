# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the StockWatch API backend (macOS)."""

import sys
from pathlib import Path

ROOT = Path(SPECPATH).parent
block_cipher = None

hiddenimports = [
    "api.server",
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "fastapi",
    "starlette",
    "pydantic",
    "pydantic_core",
    "httpx",
    "httpcore",
    "h11",
    "anyio",
    "sniffio",
    "yaml",
    "dotenv",
    "multipart",
    "email_validator",
    "watchfiles",
    "websockets",
    "discovery.johnlewis_scanner",
    "service",
    "database",
    "jl_client",
    "pc_client",
    "config_loader",
    "monitor",
    "state_store",
]

datas = [
    (str(ROOT / "api"), "api"),
    (str(ROOT / "discovery"), "discovery"),
]

a = Analysis(
    [str(ROOT / "backend_entry.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="stockwatch-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="stockwatch-backend",
)
