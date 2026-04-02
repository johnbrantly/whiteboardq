# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for WhiteboardQ Client."""

import sys
from pathlib import Path

block_cipher = None

# Get the base path (whiteboardq_client folder)
base_path = Path(SPECPATH)
# Parent is the whiteboard-q folder containing the package
project_path = base_path.parent

a = Analysis(
    [str(base_path / 'main.py')],
    pathex=[str(project_path)],  # Add project root so whiteboardq_client package is found
    binaries=[],
    datas=[
        (str(base_path / 'sounds' / '*.wav'), 'whiteboardq_client/sounds'),
        (str(base_path / 'resources' / 'icon.png'), 'whiteboardq_client/resources'),
        (str(project_path / 'version.py'), '.'),
        (str(project_path / '_version_frozen.txt'), '.'),
    ],
    hiddenimports=[
        'whiteboardq_client',
        'whiteboardq_client.app',
        'whiteboardq_client.config',
        'whiteboardq_client.theme',
        'whiteboardq_client.sounds',
        'whiteboardq_client.network',
        'whiteboardq_client.network.websocket_client',
        'whiteboardq_client.ui',
        'whiteboardq_client.ui.main_window',
        'whiteboardq_client.ui.message_list',
        'whiteboardq_client.ui.message_card',
        'whiteboardq_client.ui.control_sidebar',
        'whiteboardq_client.ui.chat_bar',
        'whiteboardq_client.ui.status_bar',
        'whiteboardq_client.ui.settings_dialog',
        'whiteboardq_client.ui.delete_dialog',
        'whiteboardq_client.ui.undo_toast',
        'PySide6.QtCore',
        'PySide6.QtWidgets',
        'PySide6.QtGui',
        'PySide6.QtMultimedia',
        'websockets',
        'websockets.client',
        'qasync',
    ],
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='WhiteboardQ',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(base_path / 'resources' / 'icon.ico'),
)
