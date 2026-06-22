"""
MetaTrader 5 Integration:
  - Verbindung aufbauen / trennen
  - Lotgrösse basierend auf Risiko % berechnen
  - Market Orders platzieren (BUY / SELL)
  - Positionen schliessen
  - Stop Loss auf Break Even verschieben
"""

import logging
from typing import Optional

import MetaTrader5 as mt5

from config import (
    BOT_MAGIC_NUMBER,
    MT5_LOGIN,
    MT5_PASSWORD,
    MT5_SERVER,
    RISK_PERCENT,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Verbindung
# ---------------------------------------------------------------------------

def connect() -> bool:
    if not mt5.initialize(login=MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER):
        logger.error(f"MT5 initialize fehlgeschlagen: {mt5.last_error()}")
        return False
    acc = mt5.account_info()
    logger.info(f"MT5 verbunden | Konto: {acc.name} | Balance: {acc.balance} {acc.currency}")
    return True


def disconnect():
    mt5.shutdown()
    logger.info("MT5 Verbindung getrennt")


def reconnect_if_needed() -> bool:
    """Stellt Verbindung wieder her falls getrennt."""
    if mt5.terminal_info() is None:
        logger.warning("MT5 Verbindung verloren - reconnect...")
        return connect()
    return True


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _get_filling_mode(symbol: str) -> int:
    """Bestimmt den vom Broker unterstützten Order-Filling-Modus."""
    info = mt5.symbol_info(symbol)
    if info is None:
        return mt5.ORDER_FILLING_IOC
    filling = info.filling_mode
    if filling & mt5.ORDER_FILLING_IOC:
        return mt5.ORDER_FILLING_IOC
    if filling & mt5.ORDER_FILLING_FOK:
        return mt5.ORDER_FILLING_FOK
    return mt5.ORDER_FILLING_RETURN


def calculate_lot_size(symbol: str, entry_price: float, sl_price: float) -> float:
    """
    Berechnet Lotgrösse so, dass bei SL-Hit genau RISK_PERCENT % des Kontos verloren gehen.
    """
    account = mt5.account_info()
    if not account:
        logger.error("Kein Account-Info verfügbar")
        return 0.0

    symbol_info = mt5.symbol_info(symbol)
    if not symbol_info:
        logger.error(f"Symbol {symbol} nicht gefunden")
        return 0.0

    risk_amount = account.balance * (RISK_PERCENT / 100.0)
    sl_distance = abs(entry_price - sl_price)

    if sl_distance == 0 or symbol_info.trade_tick_size == 0:
        logger.error("SL-Distanz oder Tick-Size ist 0")
        return 0.0

    # Anzahl Ticks bis zum SL × Wert pro Tick pro Lot = Verlust bei 1 Lot
    sl_ticks = sl_distance / symbol_info.trade_tick_size
    loss_per_lot = sl_ticks * symbol_info.trade_tick_value

    if loss_per_lot == 0:
        logger.error("Tick-Value ist 0")
        return 0.0

    raw_lot = risk_amount / loss_per_lot

    # Auf Lot-Schritte runden
    step = symbol_info.volume_step
    lot = round(raw_lot / step) * step
    lot = max(symbol_info.volume_min, min(lot, symbol_info.volume_max))

    logger.info(
        f"Lot-Berechnung {symbol}: Risiko={risk_amount:.2f} | "
        f"SL-Abstand={sl_distance} | Verlust/Lot={loss_per_lot:.2f} | Lot={lot}"
    )
    return lot


# ---------------------------------------------------------------------------
# Order-Ausführung
# ---------------------------------------------------------------------------

def place_market_order(symbol: str, direction: str, sl: float, tp: float) -> Optional[int]:
    """
    Platziert eine Market Order. Gibt die Ticket-Nummer zurück oder None bei Fehler.
    """
    if not reconnect_if_needed():
        return None

    if not mt5.symbol_select(symbol, True):
        logger.error(f"Symbol {symbol} kann nicht ausgewählt werden")
        return None

    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        logger.error(f"Kein Tick für {symbol}")
        return None

    symbol_info = mt5.symbol_info(symbol)
    digits = symbol_info.digits

    order_type  = mt5.ORDER_TYPE_BUY  if direction == "BUY"  else mt5.ORDER_TYPE_SELL
    entry_price = tick.ask            if direction == "BUY"  else tick.bid

    lot = calculate_lot_size(symbol, entry_price, sl)
    if lot <= 0:
        logger.error(f"Ungültige Lotgrösse für {symbol}")
        return None

    request = {
        "action":      mt5.TRADE_ACTION_DEAL,
        "symbol":      symbol,
        "volume":      lot,
        "type":        order_type,
        "price":       entry_price,
        "sl":          round(sl, digits),
        "tp":          round(tp, digits),
        "deviation":   30,
        "magic":       BOT_MAGIC_NUMBER,
        "comment":     "Discord Signal",
        "type_time":   mt5.ORDER_TIME_GTC,
        "type_filling": _get_filling_mode(symbol),
    }

    result = mt5.order_send(request)

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        logger.error(f"Order fehlgeschlagen | Code: {result.retcode} | {result.comment}")
        return None

    logger.info(
        f"ORDER ERÖFFNET | {direction} {lot} {symbol} @ {entry_price:.{digits}f} "
        f"| SL={sl} | TP={tp} | Ticket={result.order}"
    )
    return result.order


def close_positions_by_symbol(symbol: str):
    """Schliesst alle offenen Positionen dieses Bots für das Symbol."""
    if not reconnect_if_needed():
        return

    positions = mt5.positions_get(symbol=symbol)
    if not positions:
        logger.info(f"Keine offenen Positionen für {symbol}")
        return

    bot_positions = [p for p in positions if p.magic == BOT_MAGIC_NUMBER]
    if not bot_positions:
        logger.info(f"Keine Bot-Positionen für {symbol}")
        return

    for pos in bot_positions:
        tick       = mt5.symbol_info_tick(symbol)
        close_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
        close_price = tick.bid if pos.type == mt5.POSITION_TYPE_BUY else tick.ask

        request = {
            "action":       mt5.TRADE_ACTION_DEAL,
            "symbol":       symbol,
            "volume":       pos.volume,
            "type":         close_type,
            "position":     pos.ticket,
            "price":        close_price,
            "deviation":    30,
            "magic":        BOT_MAGIC_NUMBER,
            "comment":      "Discord Signal Close",
            "type_time":    mt5.ORDER_TIME_GTC,
            "type_filling": _get_filling_mode(symbol),
        }

        result = mt5.order_send(request)
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            logger.info(f"Position {pos.ticket} {symbol} geschlossen | PnL={pos.profit:.2f}")
        else:
            logger.error(f"Schliessen fehlgeschlagen | Ticket={pos.ticket} | Code={result.retcode}")


def move_sl_to_breakeven(symbol: str):
    """Verschiebt den Stop Loss aller Bot-Positionen für dieses Symbol auf den Einstiegspreis."""
    if not reconnect_if_needed():
        return

    positions = mt5.positions_get(symbol=symbol)
    if not positions:
        return

    symbol_info = mt5.symbol_info(symbol)
    digits = symbol_info.digits

    for pos in positions:
        if pos.magic != BOT_MAGIC_NUMBER:
            continue

        new_sl = round(pos.price_open, digits)
        if abs(new_sl - pos.sl) < symbol_info.point:
            logger.info(f"SL für Ticket {pos.ticket} bereits auf BE")
            continue

        request = {
            "action":   mt5.TRADE_ACTION_SLTP,
            "symbol":   symbol,
            "position": pos.ticket,
            "sl":       new_sl,
            "tp":       pos.tp,
        }

        result = mt5.order_send(request)
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            logger.info(f"SL auf Break Even gesetzt | Ticket={pos.ticket} | BE={new_sl}")
        else:
            logger.error(f"SL-Verschiebung fehlgeschlagen | Code={result.retcode}")
