# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for WhiteboardQ BackOffice Manager."""

import sys
from pathlib import Path

block_cipher = None

# Paths
SPEC_DIR = Path(SPECPATH)
SERVER_DIR = SPEC_DIR.parent
PROJECT_ROOT = SERVER_DIR.parent

a = Analysis(
    [str(SPEC_DIR / 'main_backoffice.py')],
    pathex=[str(PROJECT_ROOT), str(SERVER_DIR)],
    binaries=[],
    datas=[
        # Include icons
        (str(PROJECT_ROOT / 'whiteboardq_server' / 'resources' / 'icon.png'), 'whiteboardq_server/resources'),
        (str(PROJECT_ROOT / 'whiteboardq_server' / 'resources' / 'icon.ico'), 'whiteboardq_server/resources'),
        # Sound files for settings preview
        (str(PROJECT_ROOT / 'whiteboardq_client' / 'sounds'), 'whiteboardq_server/sounds'),
        # Version files
        (str(PROJECT_ROOT / 'version.py'), '.'),
        (str(PROJECT_ROOT / '_version_frozen.txt'), '.'),
    ],
    hiddenimports=[
        'whiteboardq_server',
        'whiteboardq_server.config',
        'whiteboardq_server.manager',
        'whiteboardq_server.manager.single_instance',
        'whiteboardq_server.manager.ui',
        'whiteboardq_server.manager.ui.main_window',
        'whiteboardq_server.manager.sounds',
        'PySide6.QtCore',
        'PySide6.QtMultimedia',
        'PySide6.QtWidgets',
        'PySide6.QtGui',
        'PySide6.QtNetwork',
        'cryptography',
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
    name='WhiteboardQ-BackOffice-Manager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI application - no console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(PROJECT_ROOT / 'whiteboardq_client' / 'resources' / 'icon.ico'),
)
