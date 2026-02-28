@echo off
:: ─────────────────────────────────────────────────────────────────────────────
:: Myrient Downloader — Windows launcher
:: ─────────────────────────────────────────────────────────────────────────────
:: Double-click this file to start the downloader.

title Myrient Downloader
cd /d "%~dp0"

echo.
echo   ================================================
echo     Myrient Downloader
echo   ================================================
echo.

:: ── Find a working Python 3.8+ interpreter ───────────────────────────────────
set PYTHON=

:: 1) Try the Windows Python Launcher (py.exe) — installed alongside Python
py -3 --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    py -3 -c "import sys; exit(0 if sys.version_info >= (3,8) else 1)" >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        set PYTHON=py -3
    )
)

:: 2) Try "python" command
if "%PYTHON%"=="" (
    where python >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        python -c "import sys; exit(0 if sys.version_info >= (3,8) else 1)" >nul 2>&1
        if %ERRORLEVEL% EQU 0 (
            set PYTHON=python
        )
    )
)

:: 3) Try "python3" command
if "%PYTHON%"=="" (
    where python3 >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        python3 -c "import sys; exit(0 if sys.version_info >= (3,8) else 1)" >nul 2>&1
        if %ERRORLEVEL% EQU 0 (
            set PYTHON=python3
        )
    )
)

:: ── No Python found ───────────────────────────────────────────────────────────
if "%PYTHON%"=="" (
    echo.
    echo   ================================================
    echo     Python 3.8 or newer is required
    echo   ================================================
    echo.
    echo   Python was not found on your computer.
    echo.
    echo   Steps to fix:
    echo     1. Go to: https://www.python.org/downloads/
    echo     2. Download and run the installer
    echo     3. IMPORTANT: check "Add Python to PATH"
    echo     4. Restart your computer
    echo     5. Double-click this file again
    echo.
    echo   ================================================
    echo.
    pause
    exit /b 1
)

:: ── Run the downloader ────────────────────────────────────────────────────────
for /f "tokens=*" %%v in ('%PYTHON% --version 2^>^&1') do echo   Using: %%v
echo.
%PYTHON% "%~dp0myrient_downloader.py"

echo.
pause
