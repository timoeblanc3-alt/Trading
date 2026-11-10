"""Stratégies suivies en fictif, toutes avec EXACTEMENT les règles du compte réel (agent/live.py) :
25,70 $ de départ, chaque position vaut 100 % du capital, une position à la fois, levier 3x max, ordre minimum
de 10 $, arrêt après 6 $ de perte cumulée. Seule la stratégie change d'un profil à l'autre, ce qui
permet de les comparer sur les mêmes semaines de marché, sans argent en jeu."""

from .config import Config, MarketConfig, RiskConfig
from .rotation import UNIVERSE
from .strategies import Params

LIVE_START = 25.70


def live_rules():
    return RiskConfig(risk_usd=2.0, capital_fraction=1.0, min_notional=10.0, halt_loss_usd=6.0, max_positions=1,
                      max_leverage=3.0, max_open_risk=1.0, max_correlated_risk=1.0,
                      daily_loss_limit=1.01, drawdown_halt=1.01, drawdown_reduce=0.10)


def lab_rules():
    """Règles de « laboratoire » : on veut mesurer l'avantage de la stratégie sur un maximum de trades,
    pas copier le compte réel. 1 % de risque par trade, autant de positions que de signaux, pas de
    minimum d'ordre ni de limite de corrélation. Le résultat utile est l'espérance en R."""
    return RiskConfig(risk_per_trade=0.01, max_positions=100, max_open_risk=1.0, max_correlated_risk=1.0,
                      max_leverage=100.0, daily_loss_limit=1.01, drawdown_halt=1.01, drawdown_reduce=1.01)


def _lab(name, params, coins, interval):
    base = f"paper/{name}"
    return Config(starting_equity=1000.0, risk=lab_rules(), params=params,
                  market=MarketConfig(coins=list(coins), correlated_groups=[], interval=interval, history_bars=400),
                  state_path=f"{base}/state.json", journal_path=f"{base}/journal.csv",
                  cycles_path=f"{base}/cycles.log", analyst_log_path=f"{base}/analyst.jsonl")


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


# Laboratoires : beaucoup plus de trades fictifs pour juger plus vite (capital virtuel de 1 000 $).
LABS = {
    # la stratégie actuelle sur les 30 cryptos liquides : ~10 fois plus de signaux
    "labo_30_cryptos": (Params(), UNIVERSE, "1d"),
    # la stratégie actuelle en bougies de 4 h sur BTC/ETH/SOL : ~6 fois plus de bougies
    "labo_4h": (Params(), ["BTC", "ETH", "SOL"], "4h"),
}


def configs():
    out = {name: _profile(name, p) for name, p in PROFILES.items()}
    out.update({name: _lab(name, *spec) for name, spec in LABS.items()})
    return out
