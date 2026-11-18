# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['H:/b/run_app.py'],
    pathex=['H:/b', 'H:/b/web_app'],
    binaries=[],
    datas=[('H:/b/web_app/static', 'web_app/static'), ('H:/b/web_app/static', 'static')],
    hiddenimports=['server', 'fast_check_app', 'pcd_parser', 'folder_picker', 'sync_to_unity', 'drive_sync', 'auto_box', 'numpy', 'flask', 'bridge_sync', 'static_anchor_tools', 'scipy', 'requests'],
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
    name='PJT64',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
