"""Stratégie fictive de rotation momentum : chaque semaine, on détient les 3 cryptos qui ont le plus
monté sur 14 jours, seulement si le BTC est au-dessus de sa MM200 (sinon, tout en cash).

Piste issue de docs/recherche/2026-10-18.md : positive sur 2021-2023 comme sur 2024-2026, mais avec
des baisses de 50 à 88 % et un biais du survivant dans l'historique. On la suit ici en conditions
réelles, sans argent, pour la juger sur des semaines que personne ne connaissait à l'avance."""

import json
import os

from . import hyperliquid
from . import indicators as ind

UNIVERSE = ["BTC", "ETH", "SOL", "XRP", "DOGE", "BNB", "AVAX", "LINK", "LTC", "ADA", "NEAR", "SUI", "INJ",
            "ARB", "UNI", "AAVE", "CRV", "TIA", "APT", "FET", "DOT", "ATOM", "OP", "BCH", "ETC", "FIL", "SEI",
            "WLD", "ENA", "TAO"]
LOOKBACK, TOP, HOLD_DAYS = 14, 3, 7
COST = 0.00045 + 0.0005  # frais taker + slippage, par côté
MIN_NOTIONAL = 10.0
DAY = 86_400_000
STATE = "paper/rotation/state.json"
LOG = "paper/rotation/cycles.log"


def pick(closes, btc_close, btc_ma200):
    """Les TOP actifs les plus forts sur LOOKBACK jours, ou [] si le BTC est sous sa MM200."""
    if btc_ma200 is None or btc_close <= btc_ma200:
        return []
    perf = {c: cs[-1] / cs[-1 - LOOKBACK] - 1 for c, cs in closes.items() if len(cs) > LOOKBACK + 120}
    return sorted(perf, key=perf.get, reverse=True)[:TOP]


def step(start_equity, log=print):
    st = {"cash": start_equity, "holdings": {}, "last_rebalance": 0, "start": start_equity}
    if os.path.exists(STATE):
        with open(STATE) as f:
            st = json.load(f)
    closes, last_t = {}, 0
    for c in UNIVERSE:
        try:
            cs = hyperliquid.candles(c, "1d", 220)
        except Exception:
            continue
        if cs:
            closes[c] = [x["close"] for x in cs]
            last_t = max(last_t, cs[-1]["t"])
    btc = closes["BTC"]
    ma = ind.ema(btc, 200)[-1]
    prices = {c: cs[-1] for c, cs in closes.items()}
    value = st["cash"] + sum(h["size"] * prices.get(c, h["entry"]) for c, h in st["holdings"].items())

    if last_t - st["last_rebalance"] >= HOLD_DAYS * DAY:
        target = pick(closes, btc[-1], ma)
        for c, h in list(st["holdings"].items()):  # on vend tout ce qui n'est plus dans la sélection
            if c not in target:
                st["cash"] += h["size"] * prices[c] * (1 - COST)
                del st["holdings"][c]
        value = st["cash"] + sum(h["size"] * prices[c] for c, h in st["holdings"].items())
        per = max(MIN_NOTIONAL, value / TOP) if target else 0
        for c in target:
            if c not in st["holdings"]:
                st["holdings"][c] = {"size": per / prices[c], "entry": prices[c]}
                st["cash"] -= per * (1 + COST)
        st["last_rebalance"] = last_t
        value = st["cash"] + sum(h["size"] * prices[c] for c, h in st["holdings"].items())
        regime = "BTC au-dessus de sa MM200" if target else "BTC sous sa MM200 : tout en cash"
        log(f"  Rotation : nouvelle sélection {', '.join(target) or 'aucune'} ({regime})")
    held = ", ".join(f"{c} {prices[c] / h['entry'] - 1:+.1%}" for c, h in st["holdings"].items()) or "cash"
    log(f"  Rotation : {value:.2f} $ ({value - st['start']:+.2f} $) · positions : {held}")
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE, "w") as f:
        json.dump(st, f, indent=2)
    return value
