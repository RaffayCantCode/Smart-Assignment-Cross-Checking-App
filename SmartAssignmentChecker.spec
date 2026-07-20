# -*- mode: python ; coding: utf-8 -*-
import sys
sys.setrecursionlimit(10000)

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets')],
    hiddenimports=[
        'sklearn', 
        'sklearn.metrics', 
        'sentence_transformers', 
        'fitz', 
        'docx',
        'torch',
        'nltk'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'matplotlib', 'IPython', 'jupyter', 'notebook',
        'PyQt5', 'PySide2', 'pydoc', 'unittest', 'curses'
    ],
    noarchive=False,
    optimize=1,
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
