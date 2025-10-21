# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files

block_cipher = None

# Collect all data and metadata for eth packages
datas = []
hiddenimports = []
binaries = []

# Packages that need complete collection (code + data + metadata)
packages_to_collect = [
    'eth_account',
    'eth_keys',
    'eth_utils',
    'eth_abi',
    'eth_typing',
    'eth_hash',
    'eth_rlp',
    'eth_keyfile',
    'py_ecc',
    'cytoolz',
    'toolz',
    'hexbytes',
    'rlp',
    'bitarray',
    'parsimonious',
    'Crypto',
    'ecdsa',
]

for package in packages_to_collect:
    try:
        tmp_datas, tmp_binaries, tmp_hiddenimports = collect_all(package)
        datas += tmp_datas
        binaries += tmp_binaries
        hiddenimports += tmp_hiddenimports
    except Exception as e:
        print(f"Warning: Could not collect {package}: {e}")

# Collect all service files
service_datas = [
    ('service/main.py', 'service'),
    ('service/nonce_manager.py', 'service'),  # Critical: nonce management module
    ('service/requirements.txt', 'service'),
    ('service/README.md', 'service'),
    ('service/signers/README.md', 'service/signers'),
    ('logo.png', '.'),  # Include logo in root
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
    binaries=binaries,
    datas=service_datas + datas,
    hiddenimports=hiddenimports + [
        # CustomTkinter
        'customtkinter',
        'PIL',
        'PIL._tkinter_finder',

        # Uvicorn and ASGI
        'uvicorn',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.loops.asyncio',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.http.h11_impl',
        'uvicorn.protocols.http.httptools_impl',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.protocols.websockets.wsproto_impl',
        'uvicorn.protocols.websockets.websockets_impl',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'uvicorn.server',
        'uvicorn.config',
        'uvicorn.main',

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
        'eth_account.hdaccount',
        'eth_keys',
        'eth_utils',
        'eth_abi',
        'eth_typing',
        'eth_hash',
        'eth_hash.auto',
        'eth_rlp',
        'eth_keyfile',
        'py_ecc',
        'py_ecc.secp256k1',
        'py_ecc.optimized_bn128',

        # Cryptography
        'Crypto',
        'Crypto.Hash',
        'Crypto.Cipher',
        'Crypto.Random',
        'ecdsa',

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
        'websockets',
        'httptools',
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
    name='AlphaLabsSigner',
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
    icon='logo.png' if sys.platform != 'win32' else 'logo.png',  # PyInstaller will convert PNG
)

# For macOS, create an app bundle
if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='AlphaLabsSigner.app',
        icon='logo.png',
        bundle_identifier='com.alphalabs.signer',
        info_plist={
            'CFBundleName': 'AlphaLabs Signer',
            'CFBundleDisplayName': 'AlphaLabs Signer',
            'CFBundleVersion': '1.1.0',
            'CFBundleShortVersionString': '1.1.0',
            'NSHighResolutionCapable': 'True',
            'LSBackgroundOnly': 'False',
            'NSRequiresAquaSystemAppearance': 'False',
        },
    )

