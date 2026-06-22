"""
Discord Forex Bot - Hauptprogramm

Startet den Discord Bot, überwacht den Forex-Signal-Channel
und führt Trades automatisch auf MetaTrader 5 aus.

Start: python main.py
"""

import asyncio
import logging
import sys
from logging.handlers import RotatingFileHandler

import discord

import mt5_trader
from config import CHANNEL_ID, DISCORD_BOT_TOKEN, SIGNAL_AUTHOR
from signal_parser import parse_signal, parse_update

# ---------------------------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------------------------

def setup_logging():
    fmt = logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s", "%Y-%m-%d %H:%M:%S")

    file_handler = RotatingFileHandler("bot.log", maxBytes=5_000_000, backupCount=3, encoding="utf-8")
    file_handler.setFormatter(fmt)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(fmt)

    logging.basicConfig(level=logging.INFO, handlers=[file_handler, console_handler])

setup_logging()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Discord Bot
# ---------------------------------------------------------------------------

intents = discord.Intents.default()
intents.message_content = True   # Pflicht: In Discord Dev Portal aktivieren!

client = discord.Client(intents=intents)


@client.event
async def on_ready():
    logger.info(f"Discord Bot verbunden als: {client.user}")
    logger.info(f"Überwache Channel-ID: {CHANNEL_ID} | Autor: {SIGNAL_AUTHOR}")

    loop = asyncio.get_event_loop()
    ok = await loop.run_in_executor(None, mt5_trader.connect)
    if not ok:
        logger.critical("MT5-Verbindung fehlgeschlagen! Bot läuft, aber Trades sind deaktiviert.")
    else:
        logger.info("Alles bereit. Warte auf Signale...")


@client.event
async def on_message(message: discord.Message):
    # Nur den konfigurierten Channel und Autor verarbeiten
    if message.channel.id != CHANNEL_ID:
        return
    if message.author.name != SIGNAL_AUTHOR:
        return

    text = message.content
    logger.info(f"Nachricht empfangen von {SIGNAL_AUTHOR}:\n{text}\n{'─'*50}")

    loop = asyncio.get_event_loop()

    # ---- Neues Signal? ----
    signal = parse_signal(text)
    if signal:
        logger.info(f"SIGNAL ERKANNT: {signal}")
        ticket = await loop.run_in_executor(
            None,
            mt5_trader.place_market_order,
            signal.symbol,
            signal.direction,
            signal.sl,
            signal.tp,
        )
        if ticket:
            logger.info(f"Trade erfolgreich eröffnet | Ticket: {ticket}")
        else:
            logger.error("Trade konnte NICHT eröffnet werden!")
        return

    # ---- Update (TP / SL / Close / Break Even)? ----
    update = parse_update(text)
    if update:
        logger.info(f"UPDATE ERKANNT: {update}")
        if update.action == "BREAK_EVEN":
            await loop.run_in_executor(None, mt5_trader.move_sl_to_breakeven, update.symbol)
        elif update.action in ("CLOSE", "TP_HIT"):
            await loop.run_in_executor(None, mt5_trader.close_positions_by_symbol, update.symbol)
        elif update.action == "SL_HIT":
            logger.info(f"SL getroffen für {update.symbol} - Position wurde von MT5 bereits geschlossen")
        return

    logger.debug("Nachricht enthält kein erkennbares Signal oder Update")


@client.event
async def on_disconnect():
    logger.warning("Discord Verbindung getrennt - wird automatisch neu verbunden...")


# ---------------------------------------------------------------------------
# Start
# ---------------------------------------------------------------------------

async def main():
    if DISCORD_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.critical("Bitte den DISCORD_BOT_TOKEN in config.py eintragen!")
        return

    try:
        await client.start(DISCORD_BOT_TOKEN)
    except discord.LoginFailure:
        logger.critical("Discord Login fehlgeschlagen - Token ungültig!")
    except KeyboardInterrupt:
        logger.info("Bot wird beendet...")
    finally:
        mt5_trader.disconnect()
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
