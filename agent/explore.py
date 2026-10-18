"""Exploration de stratégies sur de nombreux actifs, au niveau du trade (sans contraintes de portefeuille).

Chaque variante = un signal d'entrée de base + des filtres. Pour chaque actif, on simule chaque trade
indépendamment : entrée à l'ouverture de la bougie suivant le signal, stop et objectif en ATR, stop au
point mort à +1R puis suivi par le canal de sortie, frais et slippage inclus. Le résultat est exprimé
en R (multiples du risque initial), ce qui rend les actifs comparables entre eux.

Validation : les variantes sont classées sur la période d'apprentissage (avant `split`) et jugées
uniquement sur la période de test (après `split`), jamais vue pendant le choix."""

import json
import os
import time
from dataclasses import dataclass, field

from . import hyperliquid
from . import indicators as ind

FEE = 0.00045
SLIP = 0.0005
# Funding moyen payé par les positions acheteuses (taux de base Hyperliquid : 0,01 % par 8 h).
# Approximation : les longs le paient, les shorts le reçoivent.
FUNDING_H = 0.0000125
DAY = 86_400_000


def load_daily(coins, bars=5000, cache_dir="data/history"):
    os.makedirs(cache_dir, exist_ok=True)
    out = {}
    for coin in coins:
        path = f"{cache_dir}/hl_{coin}_1d.json"
        if os.path.exists(path) and time.time() - os.path.getmtime(path) < 86_400:
            with open(path) as f:
                out[coin] = json.load(f)
            continue
        try:
            cs = hyperliquid.candles(coin, "1d", bars)
        except Exception as e:
            print(f"  {coin}: échec du téléchargement ({e})")
            continue
        with open(path, "w") as f:
            json.dump(cs, f)
        out[coin] = cs
    return out


def features(cs):
    o = [c["open"] for c in cs]
    h = [c["high"] for c in cs]
    l = [c["low"] for c in cs]
    c = [c["close"] for c in cs]
    v = [x["volume"] for x in cs]
    up20, lo20 = ind.donchian(h, l, 20)
    up55, lo55 = ind.donchian(h, l, 55)
    up10, lo10 = ind.donchian(h, l, 10)
    atr = ind.atr(h, l, c, 14)
    atr100 = ind.sma([a if a is not None else 0.0 for a in atr], 100)
    return {
        "t": [x["t"] for x in cs], "open": o, "high": h, "low": l, "close": c, "volume": v,
        "ema20": ind.ema(c, 20), "ema50": ind.ema(c, 50), "ema200": ind.ema(c, 200),
        "atr": atr, "atr100": atr100, "adx": ind.adx(h, l, c, 14), "rsi": ind.rsi(c, 14),
        "vol20": ind.sma(v, 20),
        "up20": up20, "lo20": lo20, "up55": up55, "lo55": lo55, "up10": up10, "lo10": lo10,
    }


@dataclass
class Variant:
    name: str
    entry: int = 20              # cassure du plus haut/bas N jours
    exit: int = 10               # canal du stop suiveur
    stop_atr: float = 2.0
    target_atr: float = 4.0      # 0 = pas d'objectif fixe, sortie au stop suiveur uniquement
    shorts: bool = True
    filters: list = field(default_factory=list)


# --- filtres : (x, i, side, ctx) -> bool -----------------------------------------------------

def f_ma200(x, i, side, ctx):
    return x["close"][i] > x["ema200"][i] if side == "long" else x["close"][i] < x["ema200"][i]


def f_adx20(x, i, side, ctx):
    return x["adx"][i] is not None and x["adx"][i] >= 20


def f_adx25(x, i, side, ctx):
    return x["adx"][i] is not None and x["adx"][i] >= 25


def f_trend_stack(x, i, side, ctx):
    e20, e50, e200 = x["ema20"][i], x["ema50"][i], x["ema200"][i]
    return e20 > e50 > e200 if side == "long" else e20 < e50 < e200


def f_volume(x, i, side, ctx):
    return x["vol20"][i] is not None and x["vol20"][i] > 0 and x["volume"][i] > 1.5 * x["vol20"][i]


def f_squeeze(x, i, side, ctx):
    """Volatilité récente comprimée avant la cassure (ATR14 < ATR moyen sur 100 jours)."""
    a, b = x["atr"][i - 1], x["atr100"][i - 1]
    return a is not None and b is not None and b > 0 and a < b


def f_not_extended(x, i, side, ctx):
    """Pas d'entrée si le prix est déjà à plus de 3 ATR de l'EMA20 (cassure trop tardive)."""
    return abs(x["close"][i] - x["ema20"][i]) < 3 * x["atr"][i]


def f_btc_regime(x, i, side, ctx):
    """Le BTC doit aller dans le même sens (au-dessus/au-dessous de sa MM200)."""
    b = ctx["btc"].get(x["t"][i])
    if b is None:
        return False
    return b["close"] > b["ema200"] if side == "long" else b["close"] < b["ema200"]


def f_strong_close(x, i, side, ctx):
    """La bougie de cassure clôture dans le tiers haut (long) ou bas (short) de son range."""
    h, l, c = x["high"][i], x["low"][i], x["close"][i]
    if h == l:
        return False
    pos = (c - l) / (h - l)
    return pos > 2 / 3 if side == "long" else pos < 1 / 3


def f_breakout55(x, i, side, ctx):
    """Confirmation multi-horizons : la cassure 20 jours est aussi au-delà du canal 55 jours."""
    return x["close"][i] > x["up55"][i] if side == "long" else x["close"][i] < x["lo55"][i]


FILTERS = {
    "ma200": f_ma200, "adx20": f_adx20, "adx25": f_adx25, "trend": f_trend_stack, "volume": f_volume,
    "squeeze": f_squeeze, "not_ext": f_not_extended, "btc": f_btc_regime, "close": f_strong_close,
    "dc55": f_breakout55,
}


def _funding_r(pos, exit_t):
    hours = max(0.0, (exit_t - pos["t"]) / 3_600_000)
    cost = FUNDING_H * hours * pos["entry"]
    return (-cost if pos["side"] == "long" else cost) / pos["risk"]


def simulate(coin, x, v, ctx, start=None, end=None):
    """Trades d'une variante sur un actif. Une seule position à la fois par actif."""
    up, lo = x[f"up{v.entry}"], x[f"lo{v.entry}"]
    ex_up, ex_lo = x[f"up{v.exit}"], x[f"lo{v.exit}"]
    trades, pos = [], None
    n = len(x["close"])
    for i in range(1, n):
        t = x["t"][i]
        if pos:  # gestion de la position sur la bougie i
            o, h, l, c = x["open"][i], x["high"][i], x["low"][i], x["close"][i]
            long = pos["side"] == "long"
            exit_px = None
            if (long and o <= pos["stop"]) or (not long and o >= pos["stop"]):
                exit_px, why = o, "gap"
            elif (long and l <= pos["stop"]) or (not long and h >= pos["stop"]):
                exit_px, why = pos["stop"], "stop"
            elif pos["target"] and ((long and h >= pos["target"]) or (not long and l <= pos["target"])):
                exit_px, why = pos["target"], "objectif"
            if exit_px is not None:
                fill = exit_px * (1 - SLIP) if long else exit_px * (1 + SLIP)
                gross = (fill - pos["entry"]) if long else (pos["entry"] - fill)
                fees = FEE * (pos["entry"] + fill)
                trades.append({"coin": coin, "t": pos["t"], "side": pos["side"], "why": why,
                               "r": (gross - fees) / pos["risk"] + _funding_r(pos, t)})
                pos = None
            else:  # stop suiveur, mêmes règles que l'agent
                move = (c - pos["entry"]) if long else (pos["entry"] - c)
                if move >= pos["risk"]:
                    pos["stop"] = max(pos["stop"], pos["entry"]) if long else min(pos["stop"], pos["entry"])
                if move >= 2 * pos["risk"] and ex_lo[i] is not None:
                    pos["stop"] = max(pos["stop"], ex_lo[i]) if long else min(pos["stop"], ex_up[i])
            continue
        # recherche d'un signal à la clôture de la bougie i-1, entrée à l'ouverture de i
        j = i - 1
        if (start and x["t"][j] < start) or (end and x["t"][j] >= end):
            continue
        if up[j] is None or x["ema200"][j] is None or x["atr"][j] is None or x["adx"][j] is None:
            continue
        side = "long" if x["close"][j] > up[j] else "short" if (v.shorts and x["close"][j] < lo[j]) else None
        if not side or not all(f(x, j, side, ctx) for f in v.filters):
            continue
        atr = x["atr"][j]
        o = x["open"][i]
        entry = o * (1 + SLIP) if side == "long" else o * (1 - SLIP)
        stop = x["close"][j] - v.stop_atr * atr if side == "long" else x["close"][j] + v.stop_atr * atr
        risk = (entry - stop) if side == "long" else (stop - entry)
        if risk <= 0:
            continue
        target = 0.0
        if v.target_atr:
            target = x["close"][j] + v.target_atr * atr if side == "long" else x["close"][j] - v.target_atr * atr
        pos = {"t": t, "side": side, "entry": entry, "stop": stop, "risk": risk, "target": target}
        # la bougie d'entrée elle-même peut toucher le stop : on la gère au tour suivant via i
        # (prudent : on re-teste la bougie i immédiatement)
        h, l = x["high"][i], x["low"][i]
        if (side == "long" and l <= stop) or (side == "short" and h >= stop):
            fill = stop * (1 - SLIP) if side == "long" else stop * (1 + SLIP)
            gross = (fill - entry) if side == "long" else (entry - fill)
            trades.append({"coin": coin, "t": t, "side": side, "why": "stop",
                           "r": (gross - FEE * (entry + fill)) / risk})
            pos = None
    return trades


def summary(trades):
    n = len(trades)
    if not n:
        return {"n": 0, "win": 0.0, "exp": 0.0, "avg_win": 0.0, "avg_loss": 0.0, "pf": 0.0, "total": 0.0}
    wins = [t["r"] for t in trades if t["r"] > 0]
    losses = [t["r"] for t in trades if t["r"] <= 0]
    gl = -sum(losses)
    return {"n": n, "win": len(wins) / n, "exp": sum(t["r"] for t in trades) / n,
            "avg_win": sum(wins) / len(wins) if wins else 0.0,
            "avg_loss": sum(losses) / len(losses) if losses else 0.0,
            "pf": sum(wins) / gl if gl else float("inf"), "total": sum(t["r"] for t in trades)}


def btc_context(btc_x):
    return {t: {"close": c, "ema200": e} for t, c, e in zip(btc_x["t"], btc_x["close"], btc_x["ema200"])
            if e is not None}
