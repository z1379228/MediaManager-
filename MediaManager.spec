# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

yt_dlp_hiddenimports = (
    collect_submodules('yt_dlp.extractor')
    + collect_submodules('yt_dlp.postprocessor')
)
ejs_hiddenimports = collect_submodules('yt_dlp_ejs')
ejs_datas = collect_data_files('yt_dlp_ejs') + copy_metadata('yt-dlp-ejs')


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('mod/builtin', 'mod/builtin'),
        ('trusted_ui/assets/app-icon.png', 'trusted_ui/assets'),
        *ejs_datas,
    ],
    hiddenimports=yt_dlp_hiddenimports + ejs_hiddenimports,
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
    name='MediaManager',
    icon='assets/app-icon.ico',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
