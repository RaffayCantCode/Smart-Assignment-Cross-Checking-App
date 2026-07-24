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
        'styles',
        'pydoc'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'matplotlib', 'IPython', 'jupyter', 'notebook',
        'PyQt5', 'PySide2', 'curses',
        # Unused heavy PySide6 / Qt modules
        'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtWebEngineQuick',
        'PySide6.Qt3DCore', 'PySide6.Qt3DRender', 'PySide6.Qt3DInput', 'PySide6.Qt3DLogic', 'PySide6.Qt3DExtras', 'PySide6.Qt3DAnimation',
        'PySide6.QtQuick', 'PySide6.QtQuickWidgets', 'PySide6.QtQuick3D', 'PySide6.QtQml',
        'PySide6.QtDesigner', 'PySide6.QtHelp', 'PySide6.QtMultimedia', 'PySide6.QtMultimediaWidgets',
        'PySide6.QtPdf', 'PySide6.QtPdfWidgets', 'PySide6.QtPositioning', 'PySide6.QtLocation',
        'PySide6.QtSensors', 'PySide6.QtBluetooth', 'PySide6.QtNfc', 'PySide6.QtRemoteObjects',
        'PySide6.QtScxml', 'PySide6.QtSerialPort', 'PySide6.QtSpatialAudio', 'PySide6.QtTest',
        'PySide6.QtTextToSpeech', 'PySide6.QtVirtualKeyboard', 'PySide6.QtWebChannel', 'PySide6.QtWebSockets',
        # Unused heavy submodules
        'tensorflow', 'sympy', 'torch.distributed', 'torch.testing', 'torch.cuda', 'torch.utils.benchmark',
        'torch.ao', 'torch.fx', 'torch.export', 'torch.library', 'torch.masked', 'torch.nested',
        'torch.nn.parallel', 'torch.package', 'torch.profiler', 'torch.sparse', 'torch.special',
        'scipy.spatial', 'scipy.signal', 'scipy.sparse', 'scipy.optimize', 'scipy.stats', 'scipy.fft'
    ],
    noarchive=False,
    optimize=1,
)

# Filter out heavy unused Qt6 DLLs from binary collection
excluded_dll_prefixes = (
    'qt6webengine', 'qt6quick', 'qt63d', 'qt6qml', 'qt6designer',
    'qt6multimedia', 'qt6pdf', 'qt6bluetooth', 'qt6sensors',
    'qt6positioning', 'qt6location', 'qt6virtualkeyboard', 'qt6help',
    'qt6nfc', 'qt6scxml', 'qt6spatialaudio', 'qt6texttospeech'
)
a.binaries = [
    x for x in a.binaries
    if not any(x[0].lower().startswith(prefix) or f"\\{prefix}" in x[0].lower() for prefix in excluded_dll_prefixes)
]

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


