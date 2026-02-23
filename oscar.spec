# -*- mode: python ; coding: utf-8 -*-
"""
OSCAR PyInstaller Spec
======================
Build with:
    pyinstaller oscar.spec

Produces a --onedir bundle under dist/OSCAR/
This is then wrapped by platform-specific installer scripts.
"""

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_all, collect_submodules

# ── Collect data files for packages that need them ───────────────────────────
datas = []
binaries = []
hiddenimports = []

# Streamlit: lots of static files (HTML, JS, CSS, images)
st_datas, st_binaries, st_hidden = collect_all("streamlit")
datas    += st_datas
binaries += st_binaries
hiddenimports += st_hidden

# Plotly: bundled JS for offline rendering
datas += collect_data_files("plotly")

# Altair: Streamlit depends on it
datas += collect_data_files("altair")

# pyarrow: Streamlit uses it for Arrow-based data serialization (required)
datas += collect_data_files("pyarrow")

# Our app's own files
datas += [
    ("dashboard_aec_v2.py", "."),
    ("license_validator.py", "."),
    ("IFI_noir_logo.png", "."),
    # Empty secrets.toml so Streamlit doesn't log a warning on startup
    ("build/streamlit_config/.streamlit/secrets.toml", ".streamlit"),
    ("build/streamlit_config/.streamlit/config.toml", ".streamlit"),
]

# ── Additional hidden imports ─────────────────────────────────────────────────
hiddenimports += [
    # Core data
    "pandas",
    "pandas._libs.tslibs.base",
    "numpy",
    "openpyxl",
    "openpyxl.cell._writer",
    # Viz
    "plotly",
    "plotly.express",
    "plotly.graph_objects",
    "plotly.subplots",
    "plotly.figure_factory",
    # Streamlit internals
    "streamlit.web",
    "streamlit.web.cli",
    "streamlit.web.server",
    "streamlit.runtime",
    "streamlit.runtime.scriptrunner",
    "streamlit.runtime.legacy_caching",
    "streamlit.runtime.caching",
    "streamlit.runtime.state",
    "streamlit.components.v1",
    # Tornado (Streamlit's web server)
    "tornado",
    "tornado.web",
    "tornado.ioloop",
    "tornado.httpserver",
    "tornado.websocket",
    "tornado.escape",
    # Cryptography (license validation)
    "cryptography",
    "cryptography.hazmat.primitives",
    "cryptography.hazmat.primitives.asymmetric",
    "cryptography.hazmat.primitives.asymmetric.padding",
    "cryptography.hazmat.primitives.asymmetric.rsa",
    "cryptography.hazmat.primitives.hashes",
    "cryptography.hazmat.primitives.serialization",
    "cryptography.hazmat.backends",
    "cryptography.hazmat.backends.openssl",
    # PyWebView
    "webview",
    "webview.platforms",
    # Other
    "PIL",
    "PIL.Image",
    "click",
    "rich",
    "toml",
    "packaging",
    "packaging.version",
    "validators",
    "tzdata",
    "tkinter",
    "tkinter.messagebox",
    # pyarrow: required by Streamlit for Arrow-based data serialization
    "pyarrow",
    "pyarrow.lib",
    "pyarrow.vendored",
    "pyarrow.vendored.version",
]

# ── Platform-specific PyWebView backend ───────────────────────────────────────
if sys.platform == "darwin":
    hiddenimports += ["webview.platforms.cocoa"]
elif sys.platform == "win32":
    hiddenimports += ["webview.platforms.edgechromium", "webview.platforms.mshtml"]
else:
    hiddenimports += ["webview.platforms.gtk"]

# ── Icon paths (build scripts convert PNG to platform format first) ───────────
icon_path = None
if sys.platform == "darwin" and os.path.exists("build/icons/oscar.icns"):
    icon_path = "build/icons/oscar.icns"
elif sys.platform == "win32" and os.path.exists("build/icons/oscar.ico"):
    icon_path = "build/icons/oscar.ico"
elif os.path.exists("IFI_noir_logo.png"):
    icon_path = "IFI_noir_logo.png"

# ── Analysis ──────────────────────────────────────────────────────────────────
a = Analysis(
    ["launcher.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Heavy unused packages
        "matplotlib",
        "scipy",
        "sklearn",
        "tensorflow",
        "torch",
        "IPython",
        "jupyter",
        "notebook",
        # pywebview optional backends — macOS only needs Cocoa (pyobjc)
        "PyQt5",
        "PyQt6",
        "PySide2",
        "PySide6",
        "wx",
        "gi",          # GTK (Linux only)
        # llvmlite / numba — JIT compiler, not needed for dashboard
        "llvmlite",
        "numba",
        "numba.core",
    ],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,   # --onedir mode
    name="OSCAR",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,           # No terminal window on Windows/macOS
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,  # Set via build script for notarization
    entitlements_file=None,
    icon=icon_path,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="OSCAR",
)

# macOS: wrap in .app bundle
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="OSCAR.app",
        icon=icon_path,
        bundle_identifier="fr.institutfrancais.oscar",
        version="3.0.0",
        info_plist={
            "CFBundleName": "OSCAR",
            "CFBundleDisplayName": "OSCAR",
            "CFBundleShortVersionString": "3.0.0",
            "CFBundleVersion": "3.0.0",
            "NSHighResolutionCapable": True,
            "NSRequiresAquaSystemAppearance": False,  # supports dark mode
            "LSMinimumSystemVersion": "12.0",
            "NSHumanReadableCopyright": "© Institut français Italia",
        },
    )
