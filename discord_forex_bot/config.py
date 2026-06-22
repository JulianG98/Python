# ==============================================================
#  Discord Forex Bot - Konfiguration
#  Alle Einstellungen hier anpassen, bevor der Bot gestartet wird
# ==============================================================

# --- Discord ---
DISCORD_BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"   # Bot-Token vom Discord Developer Portal
CHANNEL_ID        = 123456789               # Rechtsklick auf #forex-midrisk -> ID kopieren
SIGNAL_AUTHOR     = "VTA_harun"             # Nur Nachrichten von diesem User werden verarbeitet

# --- MetaTrader 5 ---
MT5_LOGIN    = 12345678            # Kontonummer
MT5_PASSWORD = "your_mt5_password"
MT5_SERVER   = "YourBroker-Server" # z.B. "Pepperstone-Demo" oder "ICMarkets-Live01"

# --- Risiko-Management ---
RISK_PERCENT = 1.0   # Risiko pro Trade in % des Kontostands (z.B. 1.0 = 1%)

# --- Bot-Identifikation (nicht ändern) ---
BOT_MAGIC_NUMBER = 999001  # Eindeutige Nummer für alle Orders dieses Bots
