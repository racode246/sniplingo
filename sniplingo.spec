# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for sniplingo — one-folder Windows build.

Produces dist/sniplingo/sniplingo.exe (a windowed tray app — no console window).

Why this is non-trivial: most of sniplingo's heavy/native dependencies are imported
*lazily* (inside functions) to keep the architecture boundaries clean, so PyInstaller's
static analysis can't see them. We therefore collect them explicitly:
  - winrt.*  -> native .pyd modules for Windows OCR (collect_all)
  - mss / PIL / deep_translator / pynput -> lazily imported, added as hidden imports
argostranslate (offline fallback) and its heavy native deps are intentionally EXCLUDED;
the offline backend is opt-in and would bloat the build. Install it into the venv and
rebuild only if you want offline translation packaged.
"""

from PyInstaller.utils.hooks import collect_all, collect_submodules

datas, binaries, hiddenimports = [], [], []

# Windows OCR (PyWinRT). All native _winrt_*.pyd live under the winrt/ package.
_w_datas, _w_binaries, _w_hidden = collect_all("winrt")
datas += _w_datas
binaries += _w_binaries
hiddenimports += _w_hidden

# Lazily-imported libraries PyInstaller cannot detect statically.
hiddenimports += ["mss", "PIL.Image"]
hiddenimports += collect_submodules("deep_translator")
hiddenimports += collect_submodules("pynput")

a = Analysis(
    ["src\\sniplingo\\ui\\main.py"],
    pathex=["src"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        "argostranslate",
        "ctranslate2",
        "sentencepiece",
        "stanza",
        "torch",
        "tkinter",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SnipLingo",
    debug=False,
    strip=False,
    upx=False,
    console=False,  # tray/GUI app — no console window
    icon="assets\\sniplingo.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="SnipLingo",
)
