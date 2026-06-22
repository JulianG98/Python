# ==============================================================
#  Discord Forex Bot - Konfiguration
#  Secrets werden aus der .env Datei geladen (niemals in Git!)
# ==============================================================

import os
from dotenv import load_dotenv

load_dotenv()

# --- Discord ---
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
CHANNEL_ID        = int(os.getenv("CHANNEL_ID", "0"))
SIGNAL_AUTHOR     = os.getenv("SIGNAL_AUTHOR", "VTA_harun")

# --- MetaTrader 5 ---
MT5_LOGIN    = int(os.getenv("MT5_LOGIN", "0"))
MT5_PASSWORD = os.getenv("MT5_PASSWORD", "")
MT5_SERVER   = os.getenv("MT5_SERVER", "")

# --- Risiko-Management ---
RISK_PERCENT = float(os.getenv("RISK_PERCENT", "1.0"))

# --- Bot-Identifikation (nicht ändern) ---
BOT_MAGIC_NUMBER = 999001
