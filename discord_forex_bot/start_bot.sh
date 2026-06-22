#!/bin/bash
# =============================================================
# Bot starten (nach einmaligem wine_setup.sh)
# Verwendung: bash start_bot.sh
# =============================================================

export DISPLAY=:99
export WINEPREFIX="$HOME/.wine_mt5"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[1/3] Virtuellen Display starten..."
pkill Xvfb 2>/dev/null || true
Xvfb :99 -screen 0 1024x768x16 &
sleep 2

echo "[2/3] MetaTrader 5 starten..."
DISPLAY=:99 WINEPREFIX="$HOME/.wine_mt5" wine "$HOME/.wine_mt5/drive_c/Program Files/MetaTrader 5/terminal64.exe" &
sleep 10
echo "✓ MT5 gestartet"

echo "[3/3] Discord Bot starten..."
cd "$SCRIPT_DIR"
DISPLAY=:99 WINEPREFIX="$HOME/.wine_mt5" wine python main.py
