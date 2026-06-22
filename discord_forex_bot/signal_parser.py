"""
Parst Discord-Nachrichten von VTA_harun und erkennt:
  - Neue Trade-Signale (LONG/SHORT + SL + TP)
  - Updates (TP Hit, SL Hit, Manueller Exit, Break Even)
"""

import re
from dataclasses import dataclass
from typing import Optional

FOREX_SYMBOLS = [
    # Major Pairs
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD",
    # Cross Pairs
    "EURGBP", "EURJPY", "GBPJPY", "AUDJPY", "EURAUD", "EURCAD", "EURCHF",
    "GBPAUD", "GBPCAD", "GBPCHF", "AUDCAD", "AUDCHF", "AUDNZD", "CADJPY",
    "CHFJPY", "NZDJPY", "NZDCAD", "NZDCHF", "CADCHF",
    # Metals & Crypto
    "XAUUSD", "XAGUSD", "BTCUSD", "ETHUSD",
    # Indices
    "US30", "US500", "NAS100", "GER40", "UK100", "JP225",
]


@dataclass
class TradeSignal:
    symbol: str
    direction: str  # "BUY" oder "SELL"
    sl: float
    tp: float

    def __str__(self):
        return f"{self.direction} {self.symbol} | SL={self.sl} | TP={self.tp}"


@dataclass
class TradeUpdate:
    symbol: str
    action: str  # "CLOSE", "TP_HIT", "SL_HIT", "BREAK_EVEN"

    def __str__(self):
        return f"{self.action} @ {self.symbol}"


def _find_symbol(text: str) -> Optional[str]:
    text_upper = text.upper()
    for symbol in FOREX_SYMBOLS:
        if symbol in text_upper:
            return symbol
    return None


def parse_signal(text: str) -> Optional[TradeSignal]:
    """
    Erkennt neue Trade-Signale. Beispiel:
        LONG NZDJPY 📈
        SL 91.800
        TP 94.850
    """
    text_upper = text.upper()

    # Richtung bestimmen
    if re.search(r'\b(LONG|BUY)\b', text_upper):
        direction = "BUY"
    elif re.search(r'\b(SHORT|SELL)\b', text_upper):
        direction = "SELL"
    else:
        return None

    # Symbol suchen
    symbol = _find_symbol(text)
    if not symbol:
        return None

    # SL suchen (z.B. "SL 1.41850" oder "SL: 91.800")
    sl_match = re.search(r'\bSL[:\s]+([\d.]+)', text, re.IGNORECASE)
    if not sl_match:
        return None

    # TP suchen (nimmt erstes TP bei mehreren: TP1, TP 1, TP)
    tp_match = re.search(r'\bTP\s*\d*[:\s]+([\d.]+)', text, re.IGNORECASE)
    if not tp_match:
        return None

    return TradeSignal(
        symbol=symbol,
        direction=direction,
        sl=float(sl_match.group(1)),
        tp=float(tp_match.group(1)),
    )


def parse_update(text: str) -> Optional[TradeUpdate]:
    """
    Erkennt Trade-Updates. Beispiele:
        "EURUSD FULL TP"
        "USDCAD SL"
        "bin bei GBPCAD ausgetiegen"
        "NZDJPY SL auf Break Even ziehen"
    """
    text_upper = text.upper()

    symbol = _find_symbol(text)
    if not symbol:
        return None

    # Break Even
    if re.search(r'BREAK\s*EVEN|BEVEN|B\.?E\.?', text_upper):
        return TradeUpdate(symbol=symbol, action="BREAK_EVEN")

    # Full TP / TP Hit
    if re.search(r'FULL\s+TP|TP\s+HIT|TP\s+ERREICHT', text_upper):
        return TradeUpdate(symbol=symbol, action="TP_HIT")

    # Manueller Ausstieg (Deutsch)
    if re.search(r'AUSGE(TIEGEN|STIEGEN)|CLOSE|MANUELL', text_upper):
        return TradeUpdate(symbol=symbol, action="CLOSE")

    # SL Hit: "USDCAD SL" (Symbol + SL ohne weitere Keywords)
    # Vorsicht: Nicht verwechseln mit neuem Signal das auch SL enthält
    if re.search(r'\bSL\b', text_upper) and not re.search(r'\b(LONG|SHORT|BUY|SELL)\b', text_upper):
        if not re.search(r'\bTP\b', text_upper):  # Kein TP = kein neues Signal
            return TradeUpdate(symbol=symbol, action="SL_HIT")

    return None
