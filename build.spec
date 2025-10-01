# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from pathlib import Path

block_cipher = None

# Collect all service files
service_datas = [
    ('service/main.py', 'service'),
    ('service/requirements.txt', 'service'),
    ('service/README.md', 'service'),
    ('service/signers/README.md', 'service/signers'),
]

# Add platform-specific signer files only if they exist
if sys.platform == 'darwin':
    # macOS
    if os.path.exists('service/signers/signer-arm64.dylib'):
        service_datas.append(('service/signers/signer-arm64.dylib', 'service/signers'))
elif sys.platform == 'win32':
    # Windows
    if os.path.exists('service/signers/signer-amd64.dll'):
        service_datas.append(('service/signers/signer-amd64.dll', 'service/signers'))
elif sys.platform == 'linux':
    # Linux
    if os.path.exists('service/signers/signer-amd64.so'):
        service_datas.append(('service/signers/signer-amd64.so', 'service/signers'))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=service_datas,
    hiddenimports=[
        # CustomTkinter
        'customtkinter',
        'PIL',
        'PIL._tkinter_finder',

        # Uvicorn and ASGI
        'uvicorn',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.http.h11_impl',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.protocols.websockets.wsproto_impl',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',

        # FastAPI
        'fastapi',
        'fastapi.routing',
        'fastapi.middleware',
        'fastapi.middleware.cors',
        'fastapi.responses',
        'fastapi.encoders',

        # Starlette
        'starlette',
        'starlette.routing',
        'starlette.middleware',
        'starlette.middleware.cors',
        'starlette.responses',
        'starlette.requests',
        'starlette.applications',

        # Pydantic
        'pydantic',
        'pydantic.fields',
        'pydantic.main',
        'pydantic_core',

        # Ethereum
        'eth_account',
        'eth_account.messages',
        'eth_account.signers',
        'eth_keys',
        'eth_utils',
        'eth_abi',
        'eth_typing',
        'eth_hash',
        'eth_rlp',
        'eth_keyfile',

        # Other dependencies
        'anyio',
        'sniffio',
        'h11',
        'click',
        'typing_extensions',
        'cytoolz',
        'toolz',
        'bitarray',
        'hexbytes',
        'rlp',
        'parsimonious',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'pytest',
        'setuptools',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='LighterSigningService',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to False for windowed app (no console window)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

# For macOS, create an app bundle
if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='LighterSigningService.app',
        icon=None,
        bundle_identifier='com.alphalabs.lightersigningservice',
        info_plist={
            'CFBundleName': 'Lighter Signing Service',
            'CFBundleDisplayName': 'Lighter Signing Service',
            'CFBundleVersion': '1.1.0',
            'CFBundleShortVersionString': '1.1.0',
            'NSHighResolutionCapable': 'True',
            'LSBackgroundOnly': 'False',
            'NSRequiresAquaSystemAppearance': 'False',
        },
    )

