# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
root = Path(SPECPATH).parent

a = Analysis(
    [str(root / 'main.py')], pathex=[str(root)],
    binaries=[],
    datas=[(str(root / 'hypersolve/assets'), 'hypersolve/assets'),
           (str(root / 'hypersolve/hud/assets'), 'hypersolve/hud/assets')],
    hiddenimports=['hypersolve.desktop.dashboard_window', 'playwright.async_api'],
    hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy', 'PyQt5', 'PySide6'], noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='HyperSolve',
          debug=False, strip=False, upx=False, console=False,
          icon=str(root / 'hypersolve/assets/hypersolve.ico'),
          version=str(root / 'installer/version_info.txt'))
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='HyperSolve')
