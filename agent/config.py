"""Paramètres de l'agent. Les règles de risque reprennent la section 4.2 du bilan."""

from dataclasses import dataclass, field

from .strategies import Params


@dataclass
class RiskConfig:
    risk_per_trade: float = 0.01        # 1 % du capital risqué par trade
    max_open_risk: float = 0.03         # somme des risques ouverts
    max_positions: int = 3
    max_correlated_risk: float = 0.02   # BTC/ETH/SOL dans le même sens = un seul pari
    daily_loss_limit: float = 0.03      # arrêt jusqu'au lendemain (UTC)
    drawdown_reduce: float = 0.10       # taille divisée par 2 au-delà
    drawdown_halt: float = 0.15         # arrêt complet, revue humaine
    max_leverage: float = 3.0           # notionnel total / capital
    min_reward_risk: float = 2.0
    # Règles du compte réel : risque fixe en dollars, ordre minimum Hyperliquid, arrêt sur perte cumulée.
    risk_usd: float = None              # remplace risk_per_trade si renseigné
    min_notional: float = 0.0
    halt_loss_usd: float = None


@dataclass
class MarketConfig:
    coins: list = field(default_factory=lambda: ["BTC", "ETH", "SOL"])
    # Les grandes cryptos sont fortement corrélées : on les traite comme un seul groupe.
    correlated_groups: list = field(default_factory=lambda: [{"BTC", "ETH", "SOL"}])
    interval: str = "1d"
    history_bars: int = 400


@dataclass
class ExecutionConfig:
    taker_fee: float = 0.00045          # frais taker Hyperliquid (palier de base)
    slippage: float = 0.0005            # hypothèse prudente


@dataclass
class Config:
    starting_equity: float = 1000.0
    risk: RiskConfig = field(default_factory=RiskConfig)
    market: MarketConfig = field(default_factory=MarketConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    params: Params = field(default_factory=Params)
    # Suivi fictif versionné dans git : chaque exécution planifiée le met à jour.
    state_path: str = "paper/state.json"
    journal_path: str = "paper/journal.csv"
    cycles_path: str = "paper/cycles.log"
    analyst_log_path: str = "paper/analyst.jsonl"
