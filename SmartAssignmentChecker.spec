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
        'nltk',
        'pytesseract',
        'PIL',
        'PIL.Image',
        'backend',
        'backend.assignment_analyzer',
        'backend.domain',
        'backend.domain.document',
        'backend.domain.comparison',
        'backend.engines',
        'backend.engines.embedding_v1',
        'backend.extraction',
        'backend.extraction.pdf_extractor',
        'backend.extraction.docx_extractor',
        'backend.extraction.ocr',
        'backend.extraction.ocr.tesseract_provider',
        'backend.reporting',
        'backend.reporting.builder',
        'gui',
        'styles'
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
    upx=False,
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
    upx=False,
    upx_exclude=[],
    name='SmartAssignmentChecker',
)

