"""Ligne de commande de l'agent.

    python -m agent backtest [--bars 3000] [--interval 4h]
    python -m agent step          # un cycle de paper trading sur le marché réel
    python -m agent status        # état du portefeuille fictif
"""

import argparse
import csv
import json
import os
import time
from dataclasses import replace
from datetime import datetime, timezone

from . import analyst, backtest, hyperliquid, research, strategies
from .config import Config
from .portfolio import Portfolio, stats


def fmt_ts(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")


def print_stats(s):
    print(f"  Trades            : {s['trades']}")
    print(f"  Taux de réussite  : {s['win_rate']:.1%}")
    print(f"  Espérance         : {s['avg_r']:+.2f} R par trade "
          f"(gain moyen {s['avg_win_r']:+.2f} R, perte moyenne {s['avg_loss_r']:+.2f} R)")
    print(f"  Profit factor     : {s['profit_factor']:.2f}")
    print(f"  Rendement total   : {s['total_return']:+.1%}")
    print(f"  Drawdown maximal  : {s['max_drawdown']:.1%}")
    print(f"  Frais payés       : {s['fees']:.2f} $")


def cmd_backtest(cfg, args):
    data = {}
    for coin in cfg.market.coins:
        data[coin] = hyperliquid.candles(coin, args.interval, args.bars)
        print(f"{coin}: {len(data[coin])} bougies {args.interval} "
              f"du {fmt_ts(data[coin][0]['t'])} au {fmt_ts(data[coin][-1]['t'])}")
    s, trades, _ = backtest.run(cfg, data)
    print(f"\nBacktest, capital de départ {cfg.starting_equity:.0f} $ :")
    print_stats(s)
    if s["halted_at"]:
        print(f"  ⚠ Coupe-circuit déclenché le {fmt_ts(s['halted_at'])} : plus aucun trade ensuite")
    for strat in ("donchian", "pullback"):
        sub = [t for t in trades if t["strategy"] == strat]
        if sub:
            avg = sum(t["r"] for t in sub) / len(sub)
            win = sum(1 for t in sub if t["pnl"] > 0) / len(sub)
            print(f"  - {strat:9s}: {len(sub)} trades, réussite {win:.0%}, espérance {avg:+.2f} R")
    btc = data.get("BTC")
    if btc:
        print(f"\nRéférence : buy & hold BTC sur la période {btc[-1]['close'] / btc[0]['open'] - 1:+.1%}")


def cmd_walkforward(cfg, args):
    data = research.load(cfg, args.source, args.interval, args.bars)
    for coin, cs in data.items():
        print(f"{coin}: {len(cs)} bougies {args.interval} du {fmt_ts(cs[0]['t'])} au {fmt_ts(cs[-1]['t'])}")
    windows = research.walk_forward(cfg, data, args.train, args.test)
    print(f"\nWalk-forward : entraînement {args.train} bougies, test {args.test} bougies (hors échantillon)")
    print(f"{'période testée':25s} {'paramètres choisis':34s} {'trades':>6s} {'R moy.':>7s} {'défaut R':>9s}")
    for w in windows:
        p = w["params"]
        label = f"DC{p.dc_entry} stop{p.stop_atr:g} obj{p.target_atr:g} {'+pb' if p.pullback else 'sans pb'}"
        print(f"{fmt_ts(w['start'])[:10]} → {fmt_ts(w['end'])[:10]}  {label:34s} {w['oos']['trades']:6d} "
              f"{w['oos']['avg_r']:+7.2f} {w['baseline']['avg_r']:+9.2f}")
    opt = research.summarize([t for w in windows for t in w["oos_trades"]])
    base = research.summarize([t for w in windows for t in w["baseline_trades"]])
    for name, s in (("Paramètres optimisés", opt), ("Paramètres par défaut", base)):
        print(f"\n{name} (hors échantillon) : {s['trades']} trades, réussite {s['win_rate']:.0%}, "
              f"espérance {s['avg_r']:+.2f} R, total {s['total_r']:+.1f} R")


def load_state(cfg):
    if os.path.exists(cfg.state_path):
        with open(cfg.state_path) as f:
            return json.load(f)
    return None


def save_state(cfg, pf, last_bar):
    with open(cfg.state_path, "w") as f:
        json.dump({**pf.to_state(), "last_bar": last_bar}, f, indent=2)


def journal(cfg, trade):
    new = not os.path.exists(cfg.journal_path)
    os.makedirs(os.path.dirname(cfg.journal_path), exist_ok=True)
    with open(cfg.journal_path, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["ouverture", "fermeture", "actif", "sens", "stratégie", "entrée", "sortie",
                        "taille", "pnl", "r", "raison_sortie", "thèse"])
        w.writerow([fmt_ts(trade["opened"]), fmt_ts(trade["closed"]), trade["coin"], trade["side"],
                    trade["strategy"], f"{trade['entry']:.4f}", f"{trade['exit']:.4f}", f"{trade['size']:.6f}",
                    f"{trade['pnl']:.2f}", f"{trade['r']:.2f}", trade["exit_reason"], trade["reason"]])


def open_signal(cfg, pf, sig, now, mids, x, i, ctx):
    """Signal → contrôle du stop → analyste IA (veto seulement) → gestionnaire de risque → ouverture."""
    if not ((sig.side == "long" and sig.entry > sig.stop) or (sig.side == "short" and sig.entry < sig.stop)):
        return f"→ signal {sig.side} ignoré : prix déjà au-delà du stop"
    context = {"funding_horaire": ctx.get("funding"), "open_interest": ctx.get("open_interest"),
               "rsi14": round(x["rsi"][i], 1), "adx14": round(x["adx"][i], 1),
               "atr14": round(x["atr"][i], 4), "mm200": round(x["ema200"][i], 4)}
    verdict = analyst.review(sig, context)
    with open(cfg.analyst_log_path, "a") as f:
        f.write(json.dumps({"date": fmt_ts(now), "coin": sig.coin, "side": sig.side, "approved": verdict.approved,
                            "available": verdict.available, "summary": verdict.summary,
                            "risks": verdict.risks, "sources": verdict.sources}, ensure_ascii=False) + "\n")
    if not verdict.approved:
        return f"→ signal {sig.side} REFUSÉ par l'analyste : {verdict.summary}"
    d = pf.try_open(sig, now, mids)
    if not d.approved:
        return f"→ signal {sig.side} refusé par le risk manager : {d.reason}"
    return f"→ OUVERT {sig.side} ({sig.strategy}) : {sig.reason}, {d.reason}. Analyste : {verdict.summary}"


def cmd_step(cfg, args):
    os.makedirs(os.path.dirname(cfg.state_path), exist_ok=True)
    state = load_state(cfg)
    last_bar = (state or {}).get("last_bar", {})
    pf = Portfolio(cfg, state)
    mids = hyperliquid.mid_prices()
    ctxs = hyperliquid.asset_contexts()
    now = int(time.time() * 1000)
    lines = [f"Cycle du {fmt_ts(now)} UTC"]

    for coin in cfg.market.coins:
        cs = hyperliquid.candles(coin, cfg.market.interval, cfg.market.history_bars)
        x = strategies.compute(cs)
        i = len(cs) - 1
        bar_t = cs[i]["t"]
        funding = ctxs.get(coin, {}).get("funding", 0.0)
        new_bar = last_bar.get(coin) != bar_t
        line = f"  {coin:4s} {mids[coin]:>10,.2f}  funding {funding * 100:+.4f} %/h"

        if new_bar:
            for t in pf.manage(coin, x, i, bar_t):
                journal(cfg, t)
                line += f"  → fermé ({t['exit_reason']}) {t['r']:+.2f} R"
            last_bar[coin] = bar_t

        if any(p["coin"] == coin for p in pf.positions):
            p = next(p for p in pf.positions if p["coin"] == coin)
            line += f"  | position {p['side']} depuis {p['entry']:.2f}, stop {p['stop']:.2f}"
        elif new_bar:
            sig = strategies.best_signal(coin, x, i, funding, cfg.risk.min_reward_risk)
            if sig:
                line += "  " + open_signal(cfg, pf, replace(sig, entry=mids[coin]), now, mids, x, i, ctxs.get(coin, {}))
            else:
                line += "  | pas de setup"
        lines.append(line)

    eq = pf.mark(now, mids)
    save_state(cfg, pf, last_bar)
    lines.append(f"Capital fictif : {eq:.2f} $ (départ {cfg.starting_equity:.0f} $, plus haut {pf.peak:.2f} $)")
    print("\n".join(lines))
    with open(cfg.cycles_path, "a") as f:
        f.write("\n".join(lines) + "\n\n")


def cmd_status(cfg, args):
    state = load_state(cfg)
    if not state:
        print("Aucun état : lancez d'abord `python -m agent step`.")
        return
    pf = Portfolio(cfg, state)
    mids = hyperliquid.mid_prices()
    eq = pf.equity(mids)
    print(f"Capital fictif : {eq:.2f} $ (départ {cfg.starting_equity:.0f} $)")
    for p in pf.positions:
        print(f"  {p['coin']} {p['side']} {p['size']:.6f} @ {p['entry']:.2f}, stop {p['stop']:.2f}, "
              f"objectif {p['target']:.2f}, prix {mids[p['coin']]:.2f}")
    if pf.trades:
        print("Trades clôturés :")
        print_stats(stats(pf.trades, cfg.starting_equity, [eq]))


def main():
    ap = argparse.ArgumentParser(prog="agent")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("backtest")
    b.add_argument("--bars", type=int, default=3000)
    b.add_argument("--interval", default="4h")
    w = sub.add_parser("walkforward")
    w.add_argument("--source", choices=["hl", "binance"], default="hl")
    w.add_argument("--interval", default="1d")
    w.add_argument("--bars", type=int, default=5000)
    w.add_argument("--train", type=int, default=365)
    w.add_argument("--test", type=int, default=90)
    sub.add_parser("step")
    lv = sub.add_parser("live")
    lv.add_argument("--dry-run", action="store_true", help="calcule tout mais n'envoie aucun ordre")
    sub.add_parser("notify-test")
    et = sub.add_parser("execution-test")
    et.add_argument("--side", choices=["long", "short"], default="long")
    sub.add_parser("status")
    args = ap.parse_args()
    cfg = Config()
    if args.cmd == "live":
        from . import live
        raise SystemExit(live.main(args.dry_run))
    if args.cmd == "execution-test":
        from . import execution_test
        raise SystemExit(execution_test.run(args.side))
    if args.cmd == "notify-test":
        from . import notify
        ok = notify.send("Agent de trading", "Les notifications fonctionnent ✅", tags=["white_check_mark"])
        print("Notification envoyée." if ok else "NTFY_TOPIC absente ou envoi impossible.")
        return
    {"backtest": cmd_backtest, "walkforward": cmd_walkforward, "step": cmd_step, "status": cmd_status}[args.cmd](cfg, args)


if __name__ == "__main__":
    main()
