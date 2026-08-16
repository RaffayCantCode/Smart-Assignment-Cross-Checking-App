# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('C:\\Users\\Raffay\\Documents\\GitHub\\Smart-Assignment-Cross-Checking-App\\styles', 'styles'), ('C:\\Users\\Raffay\\Documents\\GitHub\\Smart-Assignment-Cross-Checking-App\\assets', 'assets'), ('C:\\Users\\Raffay\\Documents\\GitHub\\Smart-Assignment-Cross-Checking-App\\gui', 'gui'), ('C:\\Users\\Raffay\\Documents\\GitHub\\Smart-Assignment-Cross-Checking-App\\backend', 'backend'), ('C:\\Users\\Raffay\\Documents\\GitHub\\Smart-Assignment-Cross-Checking-App\\nltk_data', 'nltk_data')]
binaries = []
hiddenimports = ['PySide6', 'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets', 'PySide6.QtSvg', 'PySide6.QtNetwork', 'fitz', 'docx', 'sklearn', 'sklearn.feature_extraction.text', 'sklearn.metrics.pairwise', 'sklearn.utils', 'scipy', 'numpy', 'PIL', 'pytesseract', 'sentence_transformers', 'transformers', 'torch', 'nltk', 'unittest', 'unittest.mock']
tmp_ret = collect_all('transformers')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('torch')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('tokenizers')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('safetensors')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('sentence_transformers')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('sklearn')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['C:\\Users\\Raffay\\Documents\\GitHub\\Smart-Assignment-Cross-Checking-App\\main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    [],
    exclude_binaries=True,
    name='SmartAssignmentChecker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SmartAssignmentChecker',
)
