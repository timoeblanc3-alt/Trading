"""Portefeuille simulé (paper trading) : positions, frais, slippage, journal des trades en R."""

from datetime import datetime, timezone

from . import risk
from .strategies import trailing_stop


def day_of(ts_ms):
    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


class Portfolio:
    def __init__(self, cfg, state=None):
        self.cfg = cfg
        s = state or {}
        self.balance = s.get("balance", cfg.starting_equity)   # capital réalisé
        self.peak = s.get("peak", self.balance)
        self.day = s.get("day")
        self.day_start_equity = s.get("day_start_equity", self.balance)
        self.positions = s.get("positions", [])
        self.trades = s.get("trades", [])

    def to_state(self):
        return {"balance": self.balance, "peak": self.peak, "day": self.day,
                "day_start_equity": self.day_start_equity, "positions": self.positions, "trades": self.trades}

    def equity(self, prices):
        unreal = 0.0
        for p in self.positions:
            px = prices.get(p["coin"], p["entry"])
            unreal += (px - p["entry"]) * p["size"] * (1 if p["side"] == "long" else -1)
        return self.balance + unreal

    def mark(self, ts_ms, prices):
        eq = self.equity(prices)
        self.peak = max(self.peak, eq)
        d = day_of(ts_ms)
        if d != self.day:
            self.day, self.day_start_equity = d, eq
        return eq

    def _fill(self, price, side, opening):
        slip = self.cfg.execution.slippage
        buying = (side == "long") == opening
        return price * (1 + slip) if buying else price * (1 - slip)

    def try_open(self, signal, ts_ms, prices):
        eq = self.mark(ts_ms, prices)
        decision = risk.evaluate(signal, self.cfg.risk, eq, self.peak, self.day_start_equity,
                                 self.positions, self.cfg.market.correlated_groups)
        if not decision.approved:
            return decision
        fill = self._fill(signal.entry, signal.side, opening=True)
        fee = fill * decision.size * self.cfg.execution.taker_fee
        self.balance -= fee
        self.positions.append({
            "coin": signal.coin, "side": signal.side, "entry": fill, "size": decision.size,
            "stop": signal.stop, "target": signal.target, "initial_stop": signal.stop,
            "initial_risk": abs(fill - signal.stop), "strategy": signal.strategy,
            "reason": signal.reason, "opened": ts_ms, "fees": fee,
        })
        return decision

    def close(self, p, price, ts_ms, why):
        fill = self._fill(price, p["side"], opening=False)
        direction = 1 if p["side"] == "long" else -1
        fee = fill * p["size"] * self.cfg.execution.taker_fee
        pnl = (fill - p["entry"]) * p["size"] * direction - fee
        self.balance += pnl
        fees = p["fees"] + fee
        r = (pnl - p["fees"]) / (p["initial_risk"] * p["size"]) if p["initial_risk"] > 0 else 0.0
        self.positions.remove(p)
        self.trades.append({**{k: p[k] for k in ("coin", "side", "entry", "size", "initial_stop", "strategy",
                                                  "reason", "opened")},
                            "exit": fill, "closed": ts_ms, "exit_reason": why,
                            "pnl": pnl - p["fees"], "fees": fees, "r": r})
        return self.trades[-1]

    def manage(self, coin, x, i, ts_ms):
        """Gère la position ouverte sur `coin` avec la bougie i : stop, objectif, puis stop suiveur."""
        closed = []
        for p in [p for p in self.positions if p["coin"] == coin]:
            o, h, l = x["open"][i], x["high"][i], x["low"][i]
            if p["side"] == "long":
                if o <= p["stop"]:
                    closed.append(self.close(p, o, ts_ms, "stop (gap)"))
                elif l <= p["stop"]:  # hypothèse prudente : le stop est touché avant l'objectif
                    closed.append(self.close(p, p["stop"], ts_ms, "stop"))
                elif h >= p["target"]:
                    closed.append(self.close(p, p["target"], ts_ms, "objectif"))
                else:
                    p["stop"] = trailing_stop("long", x, i, p["entry"], p["stop"], p["initial_risk"])
            else:
                if o >= p["stop"]:
                    closed.append(self.close(p, o, ts_ms, "stop (gap)"))
                elif h >= p["stop"]:
                    closed.append(self.close(p, p["stop"], ts_ms, "stop"))
                elif l <= p["target"]:
                    closed.append(self.close(p, p["target"], ts_ms, "objectif"))
                else:
                    p["stop"] = trailing_stop("short", x, i, p["entry"], p["stop"], p["initial_risk"])
        return closed


def stats(trades, start_equity, equity_curve):
    n = len(trades)
    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] <= 0]
    gross_win = sum(t["pnl"] for t in wins)
    gross_loss = -sum(t["pnl"] for t in losses)
    max_dd, peak = 0.0, start_equity
    for e in equity_curve:
        peak = max(peak, e)
        max_dd = max(max_dd, 1 - e / peak)
    end = equity_curve[-1] if equity_curve else start_equity
    return {
        "trades": n,
        "win_rate": len(wins) / n if n else 0.0,
        "avg_r": sum(t["r"] for t in trades) / n if n else 0.0,
        "avg_win_r": sum(t["r"] for t in wins) / len(wins) if wins else 0.0,
        "avg_loss_r": sum(t["r"] for t in losses) / len(losses) if losses else 0.0,
        "profit_factor": gross_win / gross_loss if gross_loss else float("inf") if gross_win else 0.0,
        "total_return": end / start_equity - 1,
        "max_drawdown": max_dd,
        "fees": sum(t["fees"] for t in trades),
        "end_equity": end,
    }
