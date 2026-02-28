#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Myrient Downloader — Linux / macOS launcher
# ─────────────────────────────────────────────────────────────────────────────
# Double-click this file (or run it in a terminal) to start the downloader.
# On macOS you may need to right-click → Open the first time.

set -euo pipefail

# Move to the directory containing this script so relative paths work
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Find Python ───────────────────────────────────────────────────────────────
PYTHON=""
for cmd in python3 python3.12 python3.11 python3.10 python3.9 python3.8 python; do
    if command -v "$cmd" &>/dev/null; then
        ver=$("$cmd" -c "import sys; print(sys.version_info >= (3,8))" 2>/dev/null || echo "False")
        if [ "$ver" = "True" ]; then
            PYTHON="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo ""
    echo "╔══════════════════════════════════════════════════════╗"
    echo "║           Python 3.8+ is not installed               ║"
    echo "╠══════════════════════════════════════════════════════╣"
    echo "║                                                      ║"
    echo "║  Please install Python from:                         ║"
    echo "║    https://www.python.org/downloads/                 ║"
    echo "║                                                      ║"
    echo "║  On macOS with Homebrew:                             ║"
    echo "║    brew install python3                              ║"
    echo "║                                                      ║"
    echo "║  On Ubuntu/Debian:                                   ║"
    echo "║    sudo apt install python3 python3-pip              ║"
    echo "║                                                      ║"
    echo "╚══════════════════════════════════════════════════════╝"
    echo ""
    read -rp "Press Enter to exit..."
    exit 1
fi

echo "Using Python: $($PYTHON --version)"
echo ""

# ── Run the downloader ────────────────────────────────────────────────────────
"$PYTHON" "$SCRIPT_DIR/myrient_downloader.py"
