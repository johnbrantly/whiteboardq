# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for WhiteboardQ Server (Windows Service)."""

import sys
from pathlib import Path

block_cipher = None

# Paths
SPEC_DIR = Path(SPECPATH)
PROJECT_ROOT = SPEC_DIR.parent
SERVER_DIR = SPEC_DIR

a = Analysis(
    [str(SERVER_DIR / 'service.py')],
    pathex=[str(PROJECT_ROOT), str(SERVER_DIR)],
    binaries=[],
    datas=[
        # Include templates
        (str(SERVER_DIR / 'templates'), 'whiteboardq_server/templates'),
        # Include static files
        (str(SERVER_DIR / 'static'), 'whiteboardq_server/static'),
        # Version files
        (str(PROJECT_ROOT / 'version.py'), '.'),
        (str(PROJECT_ROOT / '_version_frozen.txt'), '.'),
    ],
    hiddenimports=[
        'whiteboardq_server',
        'whiteboardq_server.main',
        'whiteboardq_server.config',
        'whiteboardq_server.database',
        'whiteboardq_server.models',
        'whiteboardq_server.websocket_manager',
        'whiteboardq_server.routes',
        'whiteboardq_server.routes.api',
        'whiteboardq_server.routes.ws',
        'whiteboardq_server.certs',
        'cryptography',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'aiosqlite',
        'websockets',
        'multipart',
        # pywin32 for Windows Service
        'win32serviceutil',
        'win32service',
        'win32event',
        'servicemanager',
        'win32timezone',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'pkg_resources',
        'setuptools',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='WhiteboardQ-Server-Service',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Service runs without console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(PROJECT_ROOT / 'whiteboardq_server' / 'resources' / 'icon.ico'),
)
