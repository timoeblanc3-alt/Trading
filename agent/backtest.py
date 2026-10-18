"""Backtest multi-actifs : signal à la clôture d'une bougie, entrée à l'ouverture de la suivante.
Limites connues : le funding n'est pas compté, et le slippage réel peut être pire en marché agité."""

from dataclasses import replace

from . import strategies
from .portfolio import Portfolio, stats


def run(cfg, data, params=strategies.Params(), start=None, end=None, circuit_breaker=True):
    """`data` : {coin: [bougies]}. Les indicateurs sont calculés sur tout l'historique, mais on ne trade
    qu'entre `start` et `end` (timestamps ms), ce qui permet le walk-forward sans période de chauffe perdue.
    `circuit_breaker=False` mesure l'avantage brut de la stratégie, sans l'arrêt à −15 %."""
    if not circuit_breaker:
        cfg = replace(cfg, risk=replace(cfg.risk, drawdown_halt=1.01, drawdown_reduce=1.01, daily_loss_limit=1.01))
    xs = {coin: strategies.compute(c, params) for coin, c in data.items()}
    index = {coin: {c["t"]: i for i, c in enumerate(cs)} for coin, cs in data.items()}
    timeline = sorted({c["t"] for cs in data.values() for c in cs
                       if (start is None or c["t"] >= start) and (end is None or c["t"] < end)})

    pf = Portfolio(cfg)
    pending = {}
    last_close = {}
    halted_at = None
    curve = []

    for t in timeline:
        for coin, x in xs.items():
            i = index[coin].get(t)
            if i is None:
                continue
            sig = pending.pop(coin, None)
            if sig:
                o = x["open"][i]
                still_valid = (sig.side == "long" and o > sig.stop) or (sig.side == "short" and o < sig.stop)
                if still_valid:
                    d = pf.try_open(replace(sig, entry=o), t, last_close)
                    if halted_at is None and "arrêt complet" in d.reason:
                        halted_at = t
            pf.manage(coin, x, i, t)
            last_close[coin] = x["close"][i]
            if not any(p["coin"] == coin for p in pf.positions):
                s = strategies.best_signal(coin, x, i, min_rr=cfg.risk.min_reward_risk)
                if s:
                    pending[coin] = s
        curve.append(pf.mark(t, last_close))

    for p in list(pf.positions):
        pf.close(p, last_close[p["coin"]], timeline[-1], "fin du backtest")
    curve.append(pf.balance)
    return {**stats(pf.trades, cfg.starting_equity, curve), "halted_at": halted_at}, pf.trades, curve
