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

:: ── Check for Python ──────────────────────────────────────────────────────────
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    goto :no_python
)

:: Verify it's Python 3.8+
python -c "import sys; exit(0 if sys.version_info >= (3,8) else 1)" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    goto :old_python
)

:: ── Run the downloader ────────────────────────────────────────────────────────
echo   Using:  & python --version
echo.
python "%~dp0myrient_downloader.py"
goto :end

:: ── Error: Python not found ───────────────────────────────────────────────────
:no_python
echo.
echo   ╔══════════════════════════════════════════════════════╗
echo   ║         Python is not installed                      ║
echo   ╠══════════════════════════════════════════════════════╣
echo   ║                                                      ║
echo   ║  1. Go to:  https://www.python.org/downloads/        ║
echo   ║  2. Download and run the installer                   ║
echo   ║  3. IMPORTANT: check "Add Python to PATH"            ║
echo   ║  4. Restart your computer                            ║
echo   ║  5. Double-click this file again                     ║
echo   ║                                                      ║
echo   ╚══════════════════════════════════════════════════════╝
echo.
pause
exit /b 1

:: ── Error: Python too old ─────────────────────────────────────────────────────
:old_python
echo.
echo   ╔══════════════════════════════════════════════════════╗
echo   ║     Python 3.8 or newer is required                  ║
echo   ╠══════════════════════════════════════════════════════╣
echo   ║                                                      ║
echo   ║  Your Python version is too old.                     ║
echo   ║  Please download the latest Python from:             ║
echo   ║    https://www.python.org/downloads/                 ║
echo   ║                                                      ║
echo   ╚══════════════════════════════════════════════════════╝
echo.
pause
exit /b 1

:end
pause
