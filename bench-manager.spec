# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

ROOT = Path(SPECPATH)

a = Analysis(
    [str(ROOT / "tray.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        # Pre-built frontend
        (str(ROOT / "frontend" / "dist"), "frontend/dist"),
        # Backend modules
        (str(ROOT / "core"), "core"),
        (str(ROOT / "routers"), "routers"),
        (str(ROOT / "main.py"), "."),
        (str(ROOT / "config.py"), "."),
        # .env.example so first-run can copy it
        (str(ROOT / ".env.example"), "."),
    ],
    hiddenimports=[
        "uvicorn",
        "uvicorn.main",
        "uvicorn.config",
        "uvicorn.lifespan.on",
        "uvicorn.protocols.http.httptools_impl",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.websockets.websockets_impl",
        "uvicorn.loops.asyncio",
        "uvicorn.loops.uvloop",
        "fastapi",
        "starlette",
        "sse_starlette",
        "psutil",
        "pydantic_settings",
        "multipart",
        "aiofiles",
        "rumps",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="bench-manager",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # no terminal window
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="bench-manager",
)

app = BUNDLE(
    coll,
    name="Bench Manager.app",
    icon=None,  # add .icns path here when available
    bundle_identifier="io.navtech.bench-manager",
    version="1.0.0",
    info_plist={
        "NSHighResolutionCapable": True,
        "LSUIElement": True,        # hide from Dock (tray-only app)
        "NSAppleEventsUsageDescription": "Bench Manager needs automation access.",
        "CFBundleShortVersionString": "1.0.0",
    },
)
