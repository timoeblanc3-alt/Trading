"""Exécution RÉELLE sur Hyperliquid, avec le SDK officiel (hyperliquid-python-sdk).

Même stratégie que le mode fictif. Les différences tiennent à la taille du compte :
- le risque est fixé en dollars (`max_risk_usd`), pas en pourcentage, parce que Hyperliquid
  impose un ordre minimum de 10 $ et qu'à 1 % d'un petit compte aucun trade ne passerait ;
- une seule position à la fois (le budget de risque total est égal au risque d'un trade) ;
- le stop et l'objectif sont de vrais ordres déclencheurs « reduce-only » posés sur l'exchange :
  ils protègent la position même si l'agent ne tourne qu'une fois par jour ;
- marge isolée : une position ne peut jamais consommer plus que sa propre marge.

Sécurités : sans LIVE_TRADING=true, rien n'est envoyé (simulation). La présence du fichier
`live/STOP` bloque toute nouvelle ouverture (les stops déjà posés restent actifs)."""

import json
import math
import os
import time
from dataclasses import dataclass, replace

from . import analyst, hyperliquid, notify, strategies
from .config import Config

MIN_NOTIONAL = 10.0  # minimum Hyperliquid par ordre, en USDC


@dataclass
class LiveConfig:
    max_capital: float = 27.0       # capital que l'agent a le droit d'utiliser
    max_risk_usd: float = 2.0       # perte maximale par trade (et au total) si le stop est touché
    halt_loss_usd: float = 6.0      # perte cumulée qui arrête toute nouvelle ouverture (≈ 3 stops)
    max_leverage: int = 3
    entry_slippage: float = 0.01    # prix limite de l'ordre au marché
    stop_slippage: float = 0.05     # prix limite du stop une fois déclenché (priorité à l'exécution)
    state_path: str = "live/state.json"
    log_path: str = "live/cycles.log"
    journal_path: str = "live/journal.jsonl"
    stop_file: str = "live/STOP"


def round_px(px, sz_decimals):
    """Règle Hyperliquid (perps) : 5 chiffres significatifs et au plus 6 − szDecimals décimales."""
    return round(float(f"{px:.5g}"), 6 - sz_decimals)


def floor_sz(sz, sz_decimals):
    f = 10 ** sz_decimals
    return math.floor(sz * f) / f


def plan_entry(sig, mid, capital, risk_usd, lcfg, sz_decimals):
    """Taille d'un nouvel ordre. Renvoie (taille, raison du refus ou None)."""
    dist = abs(mid - sig.stop)
    if dist <= 0 or (sig.side == "long" and mid <= sig.stop) or (sig.side == "short" and mid >= sig.stop):
        return 0.0, "prix déjà au-delà du stop"
    size = risk_usd / dist
    max_notional = capital * lcfg.max_leverage
    if size * mid > max_notional:
        size = max_notional / mid
    size = floor_sz(size, sz_decimals)
    if size * mid < MIN_NOTIONAL:
        return 0.0, (f"position de {size * mid:.2f} $ sous le minimum de {MIN_NOTIONAL:.0f} $ "
                     f"(stop trop large pour {risk_usd:.2f} $ de risque)")
    return size, None


def _status(res):
    """Premier statut d'une réponse d'ordre : ('filled'|'resting'|'error', détail)."""
    if not isinstance(res, dict) or res.get("status") != "ok":
        return "error", str(res)
    st = res["response"]["data"]["statuses"][0]
    for k in ("filled", "resting"):
        if k in st:
            return k, st[k]
    return "error", st.get("error", str(st))


class LiveTrader:
    def __init__(self, exchange, info, address, lcfg=LiveConfig(), cfg=Config(), send=False, log=print):
        self.ex, self.info, self.addr = exchange, info, address
        self.lcfg, self.cfg, self.send, self.log = lcfg, cfg, send, log
        self.state = self._load()

    # --- état -------------------------------------------------------------------------------
    def _load(self):
        if os.path.exists(self.lcfg.state_path):
            with open(self.lcfg.state_path) as f:
                return json.load(f)
        return {"start_equity": None, "peak": 0.0, "positions": {}, "last_bar": {}}

    def save(self):
        os.makedirs(os.path.dirname(self.lcfg.state_path), exist_ok=True)
        with open(self.lcfg.state_path, "w") as f:
            json.dump(self.state, f, indent=2)

    def _journal(self, entry):
        os.makedirs(os.path.dirname(self.lcfg.journal_path), exist_ok=True)
        with open(self.lcfg.journal_path, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # --- ordres -----------------------------------------------------------------------------
    def _stop_orders(self, orders, coin, kind):
        return [o for o in orders if o["coin"] == coin and o.get("isTrigger") and o.get("reduceOnly")
                and kind in o.get("orderType", "")]

    def _place_trigger(self, coin, side, size, trigger, tpsl, szd):
        """Ordre déclencheur reduce-only qui ferme une position `side` (long → vente)."""
        is_buy = side == "short"
        slip = self.lcfg.stop_slippage
        limit = trigger * (1 + slip) if is_buy else trigger * (1 - slip)
        trigger, limit = round_px(trigger, szd), round_px(limit, szd)
        label = "STOP" if tpsl == "sl" else "OBJECTIF"
        if not self.send:
            self.log(f"    [simulation] {label} {coin} à {trigger}")
            return "resting", {}
        res = self.ex.order(coin, is_buy, size, limit,
                            {"trigger": {"triggerPx": trigger, "isMarket": True, "tpsl": tpsl}}, reduce_only=True)
        kind, detail = _status(res)
        self.log(f"    {label} {coin} à {trigger} : {kind} {detail if kind == 'error' else ''}")
        return kind, detail

    # --- cycle ------------------------------------------------------------------------------
    def cycle(self):
        us = self.info.user_state(self.addr)
        equity = float(us["marginSummary"]["accountValue"])
        positions = {p["position"]["coin"]: p["position"] for p in us["assetPositions"]
                     if float(p["position"]["szi"]) != 0}
        orders = self.info.frontend_open_orders(self.addr)
        meta = hyperliquid.asset_contexts()
        mids = hyperliquid.mid_prices()

        capital = min(equity, self.lcfg.max_capital)
        st = self.state
        if st["start_equity"] is None and equity > 0:
            st["start_equity"] = capital
        st["peak"] = max(st["peak"], capital)
        self.log(f"Compte : {equity:.2f} USDC (capital utilisé {capital:.2f} $, départ {st['start_equity']}) "
                 f"{'— ORDRES RÉELS' if self.send else '— simulation'}")
        if equity < MIN_NOTIONAL / self.lcfg.max_leverage:
            self.log("  ⚠ Solde perps presque vide : transférez vos USDC du compte Spot vers Perps sur Hyperliquid.")

        candles = {}
        for coin in self.cfg.market.coins:
            cs = hyperliquid.candles(coin, self.cfg.market.interval, self.cfg.market.history_bars)
            candles[coin] = (cs, strategies.compute(cs))

        # 1. Positions ouvertes : vérifier le stop, le remonter si besoin.
        for coin, (cs, x) in candles.items():
            i, bar_t = len(cs) - 1, cs[-1]["t"]
            pos = positions.get(coin)
            known = st["positions"].get(coin)
            if not pos:
                if known:
                    self.log(f"  {coin} : position fermée sur l'exchange (stop ou objectif atteint)")
                    notify.send(f"Trade fermé : {coin} {known['side']}",
                                f"Stop ou objectif atteint. Entrée {known['entry']}, stop {known['stop']:.4f}, "
                                f"objectif {known.get('target', 0):.4f}. Compte : {equity:.2f} USDC.",
                                tags=["checkered_flag"])
                    self._journal({"evt": "close", "coin": coin, "date": _now(), **known,
                                   "equity_after": equity})
                    del st["positions"][coin]
                continue
            self._manage(coin, pos, known, orders, x, i, bar_t, meta[coin]["sz_decimals"])

        # 2. Nouvelle position : une seule à la fois, uniquement sur une nouvelle bougie.
        loss = (st["start_equity"] or capital) - capital
        if os.path.exists(self.lcfg.stop_file):
            self.log("  ⛔ Fichier live/STOP présent : aucune nouvelle ouverture.")
        elif loss >= self.lcfg.halt_loss_usd:
            self.log(f"  ⛔ Perte cumulée de {loss:.2f} $ ≥ {self.lcfg.halt_loss_usd:.2f} $ : "
                     "arrêt des ouvertures, revue humaine nécessaire.")
            if not st.get("halt_notified"):
                st["halt_notified"] = True
                notify.send("Agent arrêté", f"Perte cumulée de {loss:.2f} $ : plus aucune ouverture "
                            "tant que vous n'avez pas fait le point.", priority=5, tags=["rotating_light"])
        elif positions:
            self.log("  Une position est déjà ouverte : pas de nouvelle entrée.")
        else:
            risk_usd = self.lcfg.max_risk_usd
            if st["peak"] and capital < st["peak"] * (1 - self.cfg.risk.drawdown_reduce):
                risk_usd /= 2
            for coin, (cs, x) in candles.items():
                i, bar_t = len(cs) - 1, cs[-1]["t"]
                if st["last_bar"].get(coin) == bar_t:
                    continue
                st["last_bar"][coin] = bar_t
                sig = strategies.best_signal(coin, x, i, meta[coin]["funding"], self.cfg.risk.min_reward_risk)
                if not sig:
                    self.log(f"  {coin} {mids[coin]:,.2f} : pas de setup")
                    continue
                if self._open(replace(sig, entry=mids[coin]), capital, risk_usd, x, i, meta[coin]):
                    break
        for coin, (cs, _) in candles.items():
            st["last_bar"][coin] = cs[-1]["t"]
        self.save()

    def _manage(self, coin, pos, known, orders, x, i, bar_t, szd):
        size = abs(float(pos["szi"]))
        side = "long" if float(pos["szi"]) > 0 else "short"
        entry = float(pos["entryPx"])
        stops = self._stop_orders(orders, coin, "Stop")
        if not known:  # position ouverte hors agent ou état perdu : on reconstruit prudemment
            stop = float(stops[0]["triggerPx"]) if stops else (
                entry - 2 * x["atr"][i] if side == "long" else entry + 2 * x["atr"][i])
            known = {"side": side, "entry": entry, "stop": stop, "initial_risk": abs(entry - stop),
                     "opened": _now(), "strategy": "inconnue", "last_trail_bar": None}
            self.state["positions"][coin] = known
        self.log(f"  {coin} : position {side} {size} @ {entry}, stop {known['stop']:.4f}")
        if not stops:
            self.log(f"  ⚠ {coin} : aucun stop sur l'exchange, je le replace.")
            notify.send(f"Stop manquant sur {coin}", "Aucun stop trouvé sur l'exchange : l'agent le replace.",
                        priority=4, tags=["warning"])
            self._place_trigger(coin, side, size, known["stop"], "sl", szd)
            return
        if known.get("last_trail_bar") == bar_t:
            return
        known["last_trail_bar"] = bar_t
        new = strategies.trailing_stop(side, x, i, known["entry"], known["stop"], known["initial_risk"])
        better = new > known["stop"] if side == "long" else new < known["stop"]
        if better and abs(new - known["stop"]) / known["stop"] > 0.001:
            self.log(f"  {coin} : stop suiveur {known['stop']:.4f} → {new:.4f}")
            notify.send(f"Stop remonté sur {coin}", f"{known['stop']:.4f} → {new:.4f}", priority=2,
                        tags=["arrow_up"])
            kind, _ = self._place_trigger(coin, side, size, new, "sl", szd)
            if kind != "error":  # on n'annule l'ancien stop qu'une fois le nouveau posé
                if self.send:
                    for o in stops:
                        self.ex.cancel(coin, o["oid"])
                known["stop"] = new

    def _open(self, sig, capital, risk_usd, x, i, meta):
        szd = meta["sz_decimals"]
        size, why = plan_entry(sig, sig.entry, capital, risk_usd, self.lcfg, szd)
        if why:
            self.log(f"  {sig.coin} : signal {sig.side} ignoré : {why}")
            return False
        context = {"funding_horaire": meta["funding"], "open_interest": meta["open_interest"],
                   "rsi14": round(x["rsi"][i], 1), "adx14": round(x["adx"][i], 1),
                   "atr14": round(x["atr"][i], 4), "mm200": round(x["ema200"][i], 4)}
        verdict = analyst.review(sig, context)
        self.log(f"  {sig.coin} : signal {sig.side} ({sig.reason}). Analyste : {verdict.summary}")
        if not verdict.approved:
            notify.send(f"Trade refusé par l'IA : {sig.coin} {sig.side}", verdict.summary, priority=2,
                        tags=["no_entry"])
            self._journal({"evt": "veto", "coin": sig.coin, "side": sig.side, "date": _now(),
                           "summary": verdict.summary, "sources": verdict.sources})
            return False
        self.log(f"  → OUVERTURE {sig.side} {size} {sig.coin} ≈ {sig.entry:,.4f} "
                 f"(≈ {size * sig.entry:.2f} $), stop {sig.stop:.4f}, objectif {sig.target:.4f}, "
                 f"risque ≈ {size * abs(sig.entry - sig.stop):.2f} $")
        fill_px = sig.entry
        if self.send:
            self.ex.update_leverage(self.lcfg.max_leverage, sig.coin, is_cross=False)
            kind, detail = _status(self.ex.market_open(sig.coin, sig.side == "long", size,
                                                       slippage=self.lcfg.entry_slippage))
            if kind != "filled":
                self.log(f"  ✗ Ordre non exécuté : {detail}")
                return False
            size, fill_px = float(detail["totalSz"]), float(detail["avgPx"])
            self.log(f"  ✓ Exécuté : {size} @ {fill_px}")
        kind, detail = self._place_trigger(sig.coin, sig.side, size, sig.stop, "sl", szd)
        if kind == "error":
            self.log("  ✗ Stop refusé : fermeture immédiate de la position par sécurité.")
            notify.send(f"Erreur sur {sig.coin}", "Le stop a été refusé : position fermée par sécurité.",
                        priority=5, tags=["rotating_light"])
            if self.send:
                self.ex.market_close(sig.coin)
            return False
        self._place_trigger(sig.coin, sig.side, size, sig.target, "tp", szd)
        pos = {"side": sig.side, "entry": fill_px, "size": size, "stop": sig.stop, "target": sig.target,
               "initial_risk": abs(fill_px - sig.stop), "opened": _now(), "strategy": sig.strategy,
               "reason": sig.reason, "analyst": verdict.summary, "last_trail_bar": None}
        if self.send:
            self.state["positions"][sig.coin] = pos
        if self.send:
            notify.send(f"Trade ouvert : {sig.side.upper()} {sig.coin}",
                        f"{size} {sig.coin} à {fill_px:,.4f} (≈ {size * fill_px:.2f} $)\n"
                        f"Stop {sig.stop:.4f} · Objectif {sig.target:.4f}\n"
                        f"Risque ≈ {size * abs(fill_px - sig.stop):.2f} $\n{sig.reason}\nAnalyste : {verdict.summary}",
                        priority=4, tags=["chart_with_upwards_trend" if sig.side == "long" else
                                          "chart_with_downwards_trend"])
        self._journal({"evt": "open" if self.send else "open_simulation", "coin": sig.coin, "date": _now(), **pos})
        return True


def _now():
    return time.strftime("%Y-%m-%d %H:%M", time.gmtime())


def main(dry_run_flag=False):
    key = os.environ.get("HL_API_PRIVATE_KEY")
    address = os.environ.get("HL_ACCOUNT_ADDRESS")
    if not address:
        print("HL_ACCOUNT_ADDRESS manquante : rien à faire.")
        return 1
    send = os.environ.get("LIVE_TRADING") == "true" and not dry_run_flag
    if send and not key:
        print("HL_API_PRIVATE_KEY manquante : impossible de passer des ordres.")
        return 1
    from hyperliquid.info import Info
    from hyperliquid.utils import constants

    info = Info(constants.MAINNET_API_URL, skip_ws=True)
    exchange = None
    if key:
        from eth_account import Account
        from hyperliquid.exchange import Exchange
        exchange = Exchange(Account.from_key(key), constants.MAINNET_API_URL, account_address=address)

    lcfg = LiveConfig()
    os.makedirs(os.path.dirname(lcfg.log_path), exist_ok=True)
    lines = [f"Cycle réel du {_now()} UTC"]

    def log(msg):
        print(msg)
        lines.append(msg)

    try:
        LiveTrader(exchange, info, address, lcfg, send=send, log=log).cycle()
    except Exception as e:
        notify.send("Erreur de l'agent", f"Le cycle a échoué : {e}", priority=5, tags=["rotating_light"])
        raise
    finally:
        with open(lcfg.log_path, "a") as f:
            f.write("\n".join(lines) + "\n\n")
    return 0
