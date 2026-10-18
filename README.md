# Agent de trading (Hyperliquid), mode fictif

Agent qui lit le marché Hyperliquid, applique des stratégies issues du bilan
(`docs/01-bilan-recherche-trading.md`) et gère le risque avec des règles codées en dur.
**Il ne passe aucun ordre réel** : tout est simulé (paper trading).

## Commandes

```bash
python3 -m agent backtest --bars 2500 --interval 1d   # test sur l'historique
python3 -m agent walkforward --interval 1d            # test hors échantillon (paramètres choisis sur le passé)
python3 -m agent step                                 # un cycle sur le marché réel (fictif)
python3 -m agent status                               # état du portefeuille fictif
python3 -m unittest                                   # tests
```

Python 3.10+. Seul l'analyste IA utilise une dépendance (`pip install -r requirements.txt`) et la
variable `ANTHROPIC_API_KEY` ; sans elle, il est désactivé. La stratégie est expliquée dans
`docs/02-strategie.md`.

## Automatisation

`.github/workflows/paper-trading.yml` lance un cycle chaque jour à 00:20 UTC et enregistre le
résultat dans `paper/` : `state.json` (portefeuille), `journal.csv` (trades), `cycles.log`
(historique) et `analyst.jsonl` (avis de l'IA). Pour activer l'analyste, ajoutez le secret
`ANTHROPIC_API_KEY` dans GitHub (Settings → Secrets and variables → Actions).

## Architecture

| Fichier | Rôle |
|---|---|
| `agent/hyperliquid.py` | Données publiques : prix, bougies, funding, open interest |
| `agent/indicators.py` | EMA, ATR, RSI, ADX, Donchian |
| `agent/strategies.py` | Cassure de Donchian (Turtles) et pullback en tendance, filtres MM200 / ADX / funding |
| `agent/risk.py` | Veto : 1 % de risque par trade, 3 % ouverts, 2 % sur les cryptos corrélées, levier 3x max, −3 % par jour, −10 % → taille ÷ 2, −15 % → arrêt |
| `agent/portfolio.py` | Portefeuille simulé avec frais, slippage, stops suiveurs et journal en R |
| `agent/backtest.py` | Backtest multi-actifs (entrée à l'ouverture de la bougie suivante) |
| `agent/research.py` | Walk-forward hors échantillon, historique long Binance (si le domaine est autorisé) |
| `agent/analyst.py` | Analyste Claude : recherche web, droit de veto uniquement |

## Limites connues

- Le funding n'est pas compté dans le backtest.
- Hyperliquid ne fournit que les 5 000 dernières bougies par intervalle.
- Une fois le coupe-circuit de −15 % déclenché, le backtest ne reprend plus de trade
  (comme en réel, où une revue humaine est exigée).
