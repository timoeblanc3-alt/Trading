"""Gestionnaire de risque : droit de veto absolu sur chaque proposition de trade.
Le code ici est volontairement simple et déterministe ; aucune décision n'est laissée au LLM."""

from dataclasses import dataclass


@dataclass
class Decision:
    approved: bool
    size: float = 0.0
    risk_amount: float = 0.0
    reason: str = ""


def drawdown(equity, peak):
    return 0.0 if peak <= 0 else max(0.0, 1 - equity / peak)


def position_risk(p):
    """Montant encore à risque sur une position (0 si le stop est au point mort ou au-delà)."""
    if p["side"] == "long":
        return max(0.0, (p["entry"] - p["stop"]) * p["size"])
    return max(0.0, (p["stop"] - p["entry"]) * p["size"])


def trading_halted(cfg, equity, peak, day_start_equity):
    if drawdown(equity, peak) >= cfg.drawdown_halt:
        return f"drawdown de {drawdown(equity, peak):.1%} ≥ {cfg.drawdown_halt:.0%} : arrêt complet, revue humaine nécessaire"
    if day_start_equity > 0 and 1 - equity / day_start_equity >= cfg.daily_loss_limit:
        return f"perte du jour ≥ {cfg.daily_loss_limit:.0%} : plus de trade avant demain"
    return None


def evaluate(signal, cfg, equity, peak, day_start_equity, positions, groups):
    halt = trading_halted(cfg, equity, peak, day_start_equity)
    if halt:
        return Decision(False, reason=halt)
    if any(p["coin"] == signal.coin for p in positions):
        return Decision(False, reason="position déjà ouverte sur cet actif")
    if len(positions) >= cfg.max_positions:
        return Decision(False, reason=f"maximum de {cfg.max_positions} positions atteint")
    if signal.reward_risk < cfg.min_reward_risk:
        return Decision(False, reason=f"ratio gain/risque {signal.reward_risk:.1f} < {cfg.min_reward_risk}")
    if signal.risk_per_unit <= 0:
        return Decision(False, reason="stop invalide")

    risk_pct = cfg.risk_per_trade
    if drawdown(equity, peak) >= cfg.drawdown_reduce:
        risk_pct /= 2

    budget = equity * risk_pct
    open_risk = sum(position_risk(p) for p in positions)
    budget = min(budget, equity * cfg.max_open_risk - open_risk)

    group = next((g for g in groups if signal.coin in g), None)
    if group:
        same_side = sum(position_risk(p) for p in positions if p["coin"] in group and p["side"] == signal.side)
        budget = min(budget, equity * cfg.max_correlated_risk - same_side)

    if budget <= equity * 0.001:
        return Decision(False, reason="budget de risque épuisé (risque total ou corrélé)")

    size = budget / signal.risk_per_unit
    notional_open = sum(p["size"] * p["entry"] for p in positions)
    max_notional = equity * cfg.max_leverage - notional_open
    if size * signal.entry > max_notional:
        size = max(0.0, max_notional / signal.entry)
    if size <= 0:
        return Decision(False, reason=f"levier maximal {cfg.max_leverage}x atteint")

    return Decision(True, size=size, risk_amount=size * signal.risk_per_unit,
                    reason=f"risque {size * signal.risk_per_unit / equity:.2%} du capital")
