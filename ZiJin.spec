# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None
root = os.path.dirname(os.path.abspath(SPEC))

a = Analysis(
    [os.path.join(root, 'main.py')],
    pathex=[root],
    binaries=[],
    datas=[
        (os.path.join(root, 'config'), 'config'),
        (os.path.join(root, 'models'), 'models'),
    ],
    hiddenimports=[
        'core.agent',
        'core.bus',
        'core.llm',
        'core.memory',
        'core.emotion',
        'core.log',
        'core.tool_executor',
        'core.rate_limit',
        'core.async_executor',
        'tools.registry',
        'tools.safety',
        'tools.audit',
        'tools.memo',
        'tools.todo',
        'tools.volume',
        'tools.tts',
        'tools.pc_manager',
        'tools.clock',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ZiJin',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ZiJin',
)
