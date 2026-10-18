# Agent de trading (Hyperliquid), mode fictif

Agent qui lit le marché Hyperliquid, applique des stratégies issues du bilan
(`docs/01-bilan-recherche-trading.md`) et gère le risque avec des règles codées en dur.
**Il ne passe aucun ordre réel** : tout est simulé (paper trading).

## Commandes

```bash
python3 -m agent backtest --bars 3000 --interval 4h   # test sur l'historique
python3 -m agent step                                 # un cycle sur le marché réel (fictif)
python3 -m agent status                               # état du portefeuille fictif
python3 -m unittest                                   # tests
```

Aucune dépendance externe (Python 3.10+). L'état et le journal des trades sont écrits dans `data/`.

## Architecture

| Fichier | Rôle |
|---|---|
| `agent/hyperliquid.py` | Données publiques : prix, bougies, funding, open interest |
| `agent/indicators.py` | EMA, ATR, RSI, ADX, Donchian |
| `agent/strategies.py` | Cassure de Donchian (Turtles) et pullback en tendance, filtres MM200 / ADX / funding |
| `agent/risk.py` | Veto : 1 % de risque par trade, 3 % ouverts, 2 % sur les cryptos corrélées, levier 3x max, −3 % par jour, −10 % → taille ÷ 2, −15 % → arrêt |
| `agent/portfolio.py` | Portefeuille simulé avec frais, slippage, stops suiveurs et journal en R |
| `agent/backtest.py` | Backtest multi-actifs (entrée à l'ouverture de la bougie suivante) |

## Limites connues

- Le funding n'est pas compté dans le backtest.
- Hyperliquid ne fournit que les 5 000 dernières bougies par intervalle.
- Une fois le coupe-circuit de −15 % déclenché, le backtest ne reprend plus de trade
  (comme en réel, où une revue humaine est exigée).
