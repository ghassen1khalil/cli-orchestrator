# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller specification for building the Windows executable."""
from pathlib import Path


def _resolve_project_root() -> Path:
    """Return the path used by PyInstaller when executing this spec."""

    # PyInstaller executes the spec file via ``exec`` which does not populate
    # ``__file__`` in some environments (for example when the command is run
    # from PowerShell as shown in the user's screenshot).  Falling back to the
    # current working directory guarantees the project path is resolved even
    # when ``__file__`` is missing.
    try:
        return Path(__file__).parent.resolve()  # type: ignore[name-defined]
    except NameError:
        return Path.cwd()


project_root = _resolve_project_root()

block_cipher = None


a = Analysis(
    ['app.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
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
    name='cli-orchestrator',
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
