# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec of the Lost Paradise launcher (Tk, no Qt): one folder with "$LP_SPEC_NAME.exe".
# Environment (set by packaging/windows/package-lostparadise.sh):
#   LP_SPEC_NAME  executable name   LP_SPEC_ROOT  the port/ folder
#   LP_SPEC_ICON  .ico              LP_SPEC_HIDDEN space-separated modules for --script
import os
from pathlib import Path

name = os.environ['LP_SPEC_NAME']
root = Path(os.environ['LP_SPEC_ROOT'])
icon = os.environ.get('LP_SPEC_ICON') or None
hidden = os.environ['LP_SPEC_HIDDEN'].split()

a = Analysis([str(root / 'launcher' / 'lostparadise_launcher.py')], pathex=[str(root / 'scripts')],
             datas=[(str(root / 'launcher' / 'lostparadise.png'), '.')], hiddenimports=hidden,
             excludes=['PySide6', 'shiboken6'], noarchive=False)
exe = EXE(PYZ(a.pure), a.scripts, [], exclude_binaries=True, name=name, console=False, icon=icon,
          debug=False, strip=False, upx=False)
COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name=name)
