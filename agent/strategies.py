"""Stratégies tirées du bilan : cassure de Donchian (Turtles) et pullback en tendance
(Minervini / Raschke), avec filtre de régime (MM200, ADX) et filtre de funding."""

from dataclasses import dataclass

from . import indicators as ind

# Funding horaire au-delà duquel la foule est jugée trop chargée dans un sens (~0,01 %/h ≈ 88 %/an).
FUNDING_EXTREME = 0.0001


@dataclass
class Signal:
    coin: str
    side: str           # "long" ou "short"
    entry: float
    stop: float
    target: float
    strategy: str
    reason: str

    @property
    def risk_per_unit(self):
        return abs(self.entry - self.stop)

    @property
    def reward_risk(self):
        return abs(self.target - self.entry) / self.risk_per_unit


def compute(candles):
    o = [c["open"] for c in candles]
    h = [c["high"] for c in candles]
    l = [c["low"] for c in candles]
    c = [c["close"] for c in candles]
    up20, lo20 = ind.donchian(h, l, 20)
    up10, lo10 = ind.donchian(h, l, 10)
    return {
        "open": o, "high": h, "low": l, "close": c,
        "ema20": ind.ema(c, 20), "ema50": ind.ema(c, 50), "ema200": ind.ema(c, 200),
        "atr": ind.atr(h, l, c, 14), "rsi": ind.rsi(c, 14), "adx": ind.adx(h, l, c, 14),
        "dc_up20": up20, "dc_lo20": lo20, "dc_up10": up10, "dc_lo10": lo10,
    }


def _ready(x, i, keys):
    return all(x[k][i] is not None for k in keys)


def donchian_breakout(coin, x, i, funding=0.0):
    """Turtles système 1 : cassure du plus haut/bas 20 bougies, stop 2 ATR, filtre MM200 et ADX > 20."""
    if not _ready(x, i, ["ema200", "atr", "adx", "dc_up20", "dc_lo20"]):
        return None
    close, atr = x["close"][i], x["atr"][i]
    if x["adx"][i] < 20:
        return None
    if close > x["dc_up20"][i] and close > x["ema200"][i] and funding < FUNDING_EXTREME:
        stop = close - 2 * atr
        return Signal(coin, "long", close, stop, close + 4 * atr, "donchian",
                      f"cassure du plus haut 20 bougies, au-dessus de la MM200, ADX {x['adx'][i]:.0f}")
    if close < x["dc_lo20"][i] and close < x["ema200"][i] and funding > -FUNDING_EXTREME:
        stop = close + 2 * atr
        return Signal(coin, "short", close, stop, close - 4 * atr, "donchian",
                      f"cassure du plus bas 20 bougies, sous la MM200, ADX {x['adx'][i]:.0f}")
    return None


def trend_pullback(coin, x, i, funding=0.0):
    """Tendance alignée (EMA20 > EMA50 > EMA200), retour sur l'EMA20 puis reprise. Objectif 3R."""
    if i < 1 or not _ready(x, i, ["ema20", "ema50", "ema200", "atr", "rsi"]):
        return None
    close, low, high, atr = x["close"][i], x["low"][i], x["high"][i], x["atr"][i]
    e20, e50, e200, r = x["ema20"][i], x["ema50"][i], x["ema200"][i], x["rsi"][i]
    if e20 > e50 > e200 and low <= e20 < close and 40 <= r <= 65 and funding < FUNDING_EXTREME:
        stop = min(low, e50) - 0.5 * atr
        if close - stop <= 0 or close - stop > 3 * atr:
            return None
        return Signal(coin, "long", close, stop, close + 3 * (close - stop), "pullback",
                      f"pullback sur l'EMA20 en tendance haussière, RSI {r:.0f}")
    if e20 < e50 < e200 and high >= e20 > close and 35 <= r <= 60 and funding > -FUNDING_EXTREME:
        stop = max(high, e50) + 0.5 * atr
        if stop - close <= 0 or stop - close > 3 * atr:
            return None
        return Signal(coin, "short", close, stop, close - 3 * (stop - close), "pullback",
                      f"pullback sur l'EMA20 en tendance baissière, RSI {r:.0f}")
    return None


STRATEGIES = [donchian_breakout, trend_pullback]


def best_signal(coin, x, i, funding=0.0, min_rr=2.0):
    for strat in STRATEGIES:
        s = strat(coin, x, i, funding)
        if s and s.risk_per_unit > 0 and s.reward_risk >= min_rr:
            return s
    return None


def trailing_stop(side, x, i, entry, stop, initial_risk):
    """Stop au point mort après +1R, puis suivi par le canal de Donchian 10 (sortie des Turtles)."""
    close = x["close"][i]
    new = stop
    if side == "long":
        if close - entry >= initial_risk:
            new = max(new, entry)
        if x["dc_lo10"][i] is not None and close - entry >= 2 * initial_risk:
            new = max(new, x["dc_lo10"][i])
    else:
        if entry - close >= initial_risk:
            new = min(new, entry)
        if x["dc_up10"][i] is not None and entry - close >= 2 * initial_risk:
            new = min(new, x["dc_up10"][i])
    return new
