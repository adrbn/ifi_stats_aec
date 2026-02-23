@echo off
REM ============================================================
REM OSCAR Windows Build Script
REM Produces: dist\OSCAR-3.0.0-Windows-Setup.exe
REM
REM Requirements:
REM   pip install pyinstaller pywebview cryptography pillow
REM   Inno Setup 6: https://jrsoftware.org/isdl.php  (free)
REM
REM For code signing (removes SmartScreen warning):
REM   set CODESIGN_CERT=path\to\cert.pfx
REM   set CODESIGN_PASS=your_certificate_password
REM ============================================================

setlocal EnableDelayedExpansion

set APP_NAME=OSCAR
set APP_VERSION=3.0.0
set ROOT_DIR=%~dp0..
set DIST_DIR=%ROOT_DIR%\dist
set INNO_COMPILER="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

echo ==================================================
echo   Building %APP_NAME% v%APP_VERSION% for Windows
echo ==================================================

cd /d "%ROOT_DIR%"

REM ── 1. Convert icon ──────────────────────────────────────────────────────────
echo [1/4] Converting icon...
python build\convert_icon.py 2>nul || echo     (icon conversion skipped, using PNG)

REM ── 2. Clean previous build ──────────────────────────────────────────────────
echo [2/4] Cleaning previous build...
if exist "build\OSCAR" rmdir /s /q "build\OSCAR"
if exist "dist\OSCAR" rmdir /s /q "dist\OSCAR"

REM ── 3. PyInstaller ───────────────────────────────────────────────────────────
echo [3/4] Running PyInstaller...
pyinstaller oscar.spec --noconfirm --clean
if errorlevel 1 (
    echo ERROR: PyInstaller failed.
    exit /b 1
)

REM ── 4. Code signing (optional) ───────────────────────────────────────────────
if defined CODESIGN_CERT (
    echo Signing executable...
    signtool sign ^
        /f "%CODESIGN_CERT%" ^
        /p "%CODESIGN_PASS%" ^
        /tr http://timestamp.digicert.com ^
        /td sha256 /fd sha256 ^
        "dist\OSCAR\OSCAR.exe"
    echo     Signed: dist\OSCAR\OSCAR.exe
) else (
    echo     Skipping code signing (CODESIGN_CERT not set)
)

REM ── 5. Create installer with Inno Setup ──────────────────────────────────────
echo [4/4] Creating installer...
if exist %INNO_COMPILER% (
    %INNO_COMPILER% "build\installers\windows\oscar_installer.iss"
    if errorlevel 1 (
        echo ERROR: Inno Setup failed.
        exit /b 1
    )
) else (
    echo     Inno Setup not found at %INNO_COMPILER%
    echo     Download from: https://jrsoftware.org/isdl.php
    echo     Distributable folder is at: dist\OSCAR\
)

echo.
echo ==================================================
echo   Build complete: dist\OSCAR-%APP_VERSION%-Windows-Setup.exe
echo ==================================================
