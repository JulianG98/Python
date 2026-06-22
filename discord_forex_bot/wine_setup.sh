#!/bin/bash
# =============================================================
# Wine + MT5 + Python Setup für Linux VPS (Ubuntu/Debian)
# Einmalig ausführen: bash wine_setup.sh
# =============================================================

set -e

echo "================================================"
echo " Discord Forex Bot - Wine Setup"
echo "================================================"

# --- 1. System-Pakete installieren ---
echo ""
echo "[1/6] System-Pakete installieren..."
sudo dpkg --add-architecture i386
sudo apt-get update -qq
sudo apt-get install -y \
    wine wine32 wine64 winetricks \
    xvfb x11vnc \
    wget curl unzip \
    python3 python3-pip \
    screen

echo "✓ System-Pakete installiert"

# --- 2. Xvfb Virtual Display starten ---
echo ""
echo "[2/6] Virtuellen Display starten..."
Xvfb :99 -screen 0 1024x768x16 &
export DISPLAY=:99
sleep 2
echo "✓ Virtual Display läuft auf :99"

# --- 3. Wine konfigurieren (64-bit) ---
echo ""
echo "[3/6] Wine konfigurieren..."
export WINEPREFIX="$HOME/.wine_mt5"
export WINEARCH=win64
DISPLAY=:99 winecfg /v win10 2>/dev/null || true
sleep 3
echo "✓ Wine konfiguriert (Windows 10, 64-bit)"

# --- 4. Python für Windows installieren ---
echo ""
echo "[4/6] Python 3.11 (Windows) herunterladen und installieren..."
cd /tmp
wget -q "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe" -O python_installer.exe
DISPLAY=:99 WINEPREFIX="$HOME/.wine_mt5" wine python_installer.exe \
    /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
sleep 5
echo "✓ Python installiert"

# --- 5. MetaTrader 5 herunterladen und installieren ---
echo ""
echo "[5/6] MetaTrader 5 herunterladen..."
wget -q "https://download.mql5.com/cdn/web/metaquotes.software.corp/mt5/mt5setup.exe" -O /tmp/mt5setup.exe

echo ""
echo "================================================"
echo " WICHTIG: MT5 muss jetzt manuell eingeloggt werden!"
echo ""
echo " Öffne einen zweiten Terminal und führe aus:"
echo "   x11vnc -display :99 -nopw -listen 0.0.0.0 -xkb &"
echo ""
echo " Dann verbinde dich mit einem VNC-Viewer:"
echo "   Adresse: DEINE_VPS_IP:5900"
echo ""
echo " MT5 startet in 5 Sekunden..."
echo "================================================"
sleep 5

DISPLAY=:99 WINEPREFIX="$HOME/.wine_mt5" wine /tmp/mt5setup.exe &
echo ""
echo "✓ MT5 Installer gestartet - bitte im VNC-Fenster einloggen"
echo ""
echo "  Konto:   10575412"
echo "  Server:  QuantTekel-Server"
echo ""
read -p "Drücke ENTER wenn du in MT5 eingeloggt bist und es verbunden ist..."

# --- 6. Python-Pakete unter Wine installieren ---
echo ""
echo "[6/6] Python-Pakete unter Wine installieren..."
DISPLAY=:99 WINEPREFIX="$HOME/.wine_mt5" wine python -m pip install \
    discord.py MetaTrader5 python-dotenv --quiet

echo ""
echo "================================================"
echo " Setup abgeschlossen!"
echo ""
echo " Bot starten mit:"
echo "   bash start_bot.sh"
echo "================================================"
