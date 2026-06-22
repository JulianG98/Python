# Discord Forex Bot - Setup Anleitung

## Voraussetzungen
- Windows PC mit MetaTrader 5 installiert
- Python 3.10+ installiert (python.org)
- Discord Account mit Zugang zum Signal-Channel

---

## Schritt 1: Discord Bot erstellen

1. Gehe zu https://discord.com/developers/applications
2. Klicke **"New Application"** → gib einen Namen ein (z.B. "Forex Signal Bot")
3. Links auf **"Bot"** klicken
4. Klicke **"Reset Token"** → Token kopieren → in `config.py` bei `DISCORD_BOT_TOKEN` eintragen
5. Unter **"Privileged Gateway Intents"** aktivieren:
   - ✅ **Message Content Intent** (wichtig!)
6. Bot zum Server einladen:
   - Links auf **"OAuth2"** → **"URL Generator"**
   - Scopes: ✅ `bot`
   - Bot Permissions: ✅ `Read Messages/View Channels`, ✅ `Read Message History`
   - Generierten Link öffnen → Bot zum Server hinzufügen

> **Hinweis:** Du brauchst Admin-Rechte im Server ODER der Server-Admin muss den Bot einladen.

---

## Schritt 2: Channel-ID herausfinden

1. Discord öffnen → **Einstellungen** → **Erscheinungsbild** → **Entwicklermodus** aktivieren
2. Rechtsklick auf **#forex-midrisk** → **"ID kopieren"**
3. Zahl in `config.py` bei `CHANNEL_ID` eintragen

---

## Schritt 3: config.py ausfüllen

```python
DISCORD_BOT_TOKEN = "dein_token_hier"
CHANNEL_ID        = 1234567890123456789   # deine Channel-ID
SIGNAL_AUTHOR     = "VTA_harun"

MT5_LOGIN    = 12345678
MT5_PASSWORD = "dein_mt5_passwort"
MT5_SERVER   = "DeinBroker-Server"        # Findest du in MT5 unter Datei -> Handelskonten

RISK_PERCENT = 1.0   # 1% Risiko pro Trade
```

---

## Schritt 4: Pakete installieren

Eingabeaufforderung (cmd) öffnen:

```
pip install discord.py MetaTrader5
```

---

## Schritt 5: Bot starten

1. MetaTrader 5 öffnen und einloggen (muss im Hintergrund laufen!)
2. Bot starten:

```
python main.py
```

Du siehst dann:
```
2026-06-22 20:00:00 | INFO     | Discord Bot verbunden als: Forex Signal Bot#1234
2026-06-22 20:00:00 | INFO     | MT5 verbunden | Konto: Max Mustermann | Balance: 1000.00 EUR
2026-06-22 20:00:00 | INFO     | Alles bereit. Warte auf Signale...
```

---

## Was der Bot automatisch macht

| Signal/Nachricht         | Aktion                                      |
|--------------------------|---------------------------------------------|
| `LONG NZDJPY SL 91.8 TP 94.85` | BUY Market Order mit SL + TP        |
| `SHORT USDCAD SL 1.418 TP 1.385` | SELL Market Order mit SL + TP      |
| `EURUSD FULL TP`         | Position schliessen (TP erreicht)           |
| `USDCAD SL`              | Nur loggen (MT5 hat bereits geschlossen)    |
| `SL auf Break Even`      | SL wird auf Einstiegspreis verschoben       |
| `bin bei GBPCAD ausgetiegen` | Position manuell schliessen            |

---

## Bot als Autostart einrichten (Windows)

Damit der Bot nach PC-Neustart automatisch startet:

1. `bot_start.bat` erstellen mit Inhalt:
   ```
   @echo off
   cd C:\Pfad\zu\discord_forex_bot
   python main.py
   ```
2. `Win + R` → `shell:startup` → `bot_start.bat` dort ablegen

---

## Logs prüfen

Alle Aktivitäten werden in `bot.log` gespeichert (max. 5 MB, 3 Backups).
