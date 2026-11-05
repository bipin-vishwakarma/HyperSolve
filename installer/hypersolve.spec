# -*- mode: python ; coding: utf-8 -*-
import os
import sys

block_cipher = None

a = Analysis(
    ['../main.py'],
    pathex=['..'],
    binaries=[],
    datas=[
        ('../hypersolve/hud/assets', 'hypersolve/hud/assets'),
    ],
    hiddenimports=[
        'playwright',
        'playwright.async_api',
        'requests',
        'urllib.parse',
        'hypersolve',
        'hypersolve.core.daemon',
        'hypersolve.router.brain_router',
        'hypersolve.router.session_pool',
        'hypersolve.parser.a11y_engine',
        'hypersolve.injector.synthetic_events',
        'hypersolve.stealth.ghost_shield',
        'hypersolve.hud.injector',
        'hypersolve.updater.engine',
        'hypersolve.desktop.tray',
        'hypersolve.desktop.dashboard_window',
        'PyQt6',
        'PyQt6.QtWidgets',
        'PyQt6.QtGui',
        'PyQt6.QtCore',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy'],
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
    name='HyperSolve',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
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
    upx=True,
    upx_exclude=[],
    name='HyperSolve',
)
