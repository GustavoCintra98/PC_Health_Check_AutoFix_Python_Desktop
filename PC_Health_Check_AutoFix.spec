# -*- mode: python ; coding: utf-8 -*-
# Gere o executável com: build_exe.bat  (ou: python -m PyInstaller --clean --noconfirm PC_Health_Check_AutoFix.spec)
from PyInstaller.utils.hooks import collect_data_files

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    # Temas/fontes do CustomTkinter precisam ser empacotados junto
    datas=collect_data_files('customtkinter'),
    hiddenimports=['wmi', 'win32timezone', 'pythoncom', 'pywintypes'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pytest'],
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
    name='PC_Health_Check_AutoFix',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    # UPX desativado: executáveis comprimidos com UPX que pedem Admin geram muitos falsos positivos em antivírus
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=True,
)
