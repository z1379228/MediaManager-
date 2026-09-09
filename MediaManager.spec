# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

from core.security.release_layout import pinned_builtin_pyinstaller_datas

yt_dlp_hiddenimports = (
    collect_submodules('yt_dlp.extractor')
    + collect_submodules('yt_dlp.postprocessor')
)
ejs_hiddenimports = collect_submodules('yt_dlp_ejs')
ejs_datas = collect_data_files('yt_dlp_ejs') + copy_metadata('yt-dlp-ejs')
curl_hiddenimports = collect_submodules('curl_cffi')
curl_datas = collect_data_files('curl_cffi') + copy_metadata('curl-cffi')
builtin_mod_datas = pinned_builtin_pyinstaller_datas(Path(SPECPATH))
package_layout = os.environ.get(
    'MEDIAMANAGER_PYINSTALLER_LAYOUT',
    'onefile',
)
if package_layout not in {'onefile', 'onedir'}:
    raise ValueError(
        'MEDIAMANAGER_PYINSTALLER_LAYOUT must be onefile or onedir'
    )


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        *builtin_mod_datas,
        ('trusted_ui/assets/app-icon.png', 'trusted_ui/assets'),
        *ejs_datas,
        *curl_datas,
    ],
    hiddenimports=yt_dlp_hiddenimports + ejs_hiddenimports + curl_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe_options = dict(
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

if package_layout == 'onefile':
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        **exe_options,
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        **exe_options,
    )
    collect = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='MediaManager',
    )
