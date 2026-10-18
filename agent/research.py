"""Recherche hors échantillon (walk-forward) : on choisit les paramètres sur une fenêtre passée,
puis on les teste sur la fenêtre suivante, jamais vue. Seuls les résultats hors échantillon comptent."""

import itertools
import json
import os
import time
import urllib.request

from . import backtest, hyperliquid
from .strategies import Params

GRID = [Params(dc_entry=e, stop_atr=s, target_atr=t, pullback=pb)
        for e, s, t, pb in itertools.product([20, 55], [2.0, 3.0], [4.0, 8.0], [True, False])]

BINANCE_URL = "https://data-api.binance.vision/api/v3/klines"
INTERVAL_MS = hyperliquid.INTERVAL_MS


def binance_candles(coin, interval, since_ms):
    """Historique long (Binance, paires USDT au comptant), mis en cache dans data/history/."""
    path = f"data/history/binance_{coin}_{interval}.json"
    if os.path.exists(path) and time.time() - os.path.getmtime(path) < 86_400:
        with open(path) as f:
            return json.load(f)
    out, start = [], since_ms
    while True:
        url = f"{BINANCE_URL}?symbol={coin}USDT&interval={interval}&startTime={start}&limit=1000"
        with urllib.request.urlopen(url, timeout=30) as resp:
            rows = json.loads(resp.read())
        if not rows:
            break
        out += [{"t": r[0], "close_time": r[6], "open": float(r[1]), "high": float(r[2]),
                 "low": float(r[3]), "close": float(r[4]), "volume": float(r[5])} for r in rows]
        if len(rows) < 1000:
            break
        start = rows[-1][0] + INTERVAL_MS[interval]
    now = int(time.time() * 1000)
    out = [c for c in out if c["close_time"] < now]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(out, f)
    return out


def load(cfg, source, interval, bars):
    if source == "binance":
        since = int(time.mktime((2018, 1, 1, 0, 0, 0, 0, 0, 0)) * 1000)
        return {coin: binance_candles(coin, interval, since) for coin in cfg.market.coins}
    return {coin: hyperliquid.candles(coin, interval, bars) for coin in cfg.market.coins}


def score(s, min_trades):
    """Espérance en R, pénalisée si trop peu de trades pour être crédible."""
    return s["avg_r"] if s["trades"] >= min_trades else -1.0


def walk_forward(cfg, data, train_bars, test_bars, min_trades=10):
    timeline = sorted({c["t"] for cs in data.values() for c in cs})
    warmup = 220  # MM200 + marge
    windows = []
    k = warmup + train_bars
    while k + 1 < len(timeline):
        tr_start, tr_end = timeline[k - train_bars], timeline[k]
        te_end = timeline[min(k + test_bars, len(timeline) - 1)]
        best = max(GRID, key=lambda p: score(
            backtest.run(cfg, data, p, tr_start, tr_end, circuit_breaker=False)[0], min_trades))
        oos, trades, _ = backtest.run(cfg, data, best, tr_end, te_end, circuit_breaker=False)
        base, base_trades, _ = backtest.run(cfg, data, Params(), tr_end, te_end, circuit_breaker=False)
        windows.append({"start": tr_end, "end": te_end, "params": best, "oos": oos, "oos_trades": trades,
                        "baseline": base, "baseline_trades": base_trades})
        k += test_bars
    return windows


def summarize(trades):
    n = len(trades)
    if not n:
        return {"trades": 0, "avg_r": 0.0, "win_rate": 0.0, "total_r": 0.0}
    return {"trades": n, "avg_r": sum(t["r"] for t in trades) / n,
            "win_rate": sum(1 for t in trades if t["pnl"] > 0) / n, "total_r": sum(t["r"] for t in trades)}
