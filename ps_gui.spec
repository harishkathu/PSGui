# -*- mode: python ; coding: utf-8 -*-
import subprocess
import shutil

# Generate layout.py and resources_rc.py
subprocess.run(['pyuic5', '-o', 'layout.py', './Layout.ui',], shell=True)
subprocess.run(['pyrcc5', '-o', 'resources_rc.py', './resources.qrc',], shell=True)

a = Analysis(
    ['ps_gui.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='PSGui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    icon='electric.ico',
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# Copy README.md to dist
shutil.copyfile('README.md', '{0}/README.md'.format(DISTPATH))
