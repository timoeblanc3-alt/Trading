"""Stratégies suivies en fictif, toutes avec EXACTEMENT les règles du compte réel (agent/live.py) :
25,70 $ de départ, 2 $ de risque par trade, une position à la fois, levier 3x max, ordre minimum
de 10 $, arrêt après 6 $ de perte cumulée. Seule la stratégie change d'un profil à l'autre, ce qui
permet de les comparer sur les mêmes semaines de marché, sans argent en jeu."""

from .config import Config, RiskConfig
from .strategies import Params

LIVE_START = 25.70


def live_rules():
    return RiskConfig(risk_usd=2.0, min_notional=10.0, halt_loss_usd=6.0, max_positions=1,
                      max_leverage=3.0, max_open_risk=1.0, max_correlated_risk=1.0,
                      daily_loss_limit=1.01, drawdown_halt=1.01, drawdown_reduce=0.10)


def _profile(name, params):
    base = f"paper/{name}"
    return Config(starting_equity=LIVE_START, risk=live_rules(), params=params,
                  state_path=f"{base}/state.json", journal_path=f"{base}/journal.csv",
                  cycles_path=f"{base}/cycles.log", analyst_log_path=f"{base}/analyst.jsonl")


PROFILES = {
    # copie conforme du réel : sert à détecter tout écart d'exécution
    "actuelle": Params(),
    # piste « laisser courir » : cassure 55 jours, long seulement, pas d'objectif, sortie sur le canal 20 jours
    "laisser_courir": Params(dc_entry=55, dc_exit=20, target_atr=0.0, long_only=True),
}


def configs():
    return {name: _profile(name, p) for name, p in PROFILES.items()}
