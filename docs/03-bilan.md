# Bilan du projet : agent de trading autonome (18/10/2026)

## Ce que vous avez demandé, et ce qui a été fait

| Votre demande | Ce qui a été fait | État |
|---|---|---|
| Récolter un maximum d'infos sur les grands traders et leurs méthodes | Bilan de 20 traders (Livermore, Tudor Jones, Soros, Druckenmiller, Simons, Turtles, Minervini…), méthodes d'analyse, gestion du risque, psychologie, résultats des IA qui tradent | ✅ `docs/01-bilan-recherche-trading.md` |
| Un agent qui analyse le marché comme un expert | Stratégie de suivi de tendance (méthode des Turtles), filtres MM200, ADX et funding, analyste IA Claude qui peut refuser un trade (si une clé Anthropic est ajoutée) | ✅ `docs/02-strategie.md` |
| Se connecter à votre compte Hyperliquid | Clé API « trader sans retirer », secrets GitHub, compte unifié pris en charge | ✅ |
| Prendre les trades automatiquement | Cycle réel chaque jour à 02:25 (Paris), stop et objectif posés sur l'exchange | ✅ actif |
| 27 $ de capital, 2 $ de risque max | Une position à la fois, levier 3x max, marge isolée, arrêt après 6 $ de perte | ✅ |
| Être prévenu à chaque trade sur le téléphone | Notifications ntfy : ouverture, fermeture, stop remonté, refus de l'IA, erreurs, arrêt | ✅ testé |
| Prendre un trade aujourd'hui pour vérifier que tout marche | Aller-retour réel sur BTC (≈ 11,50 $), stop et objectif posés puis vérifiés, position refermée. Coût ≈ 1 centime | ✅ réussi |
| Continuer à améliorer la stratégie en arrière-plan | Session de recherche automatique chaque dimanche à 7h47 : rapport + proposition, appliquée seulement avec votre accord | ✅ 1re le 25/10 |
| Pas un trade par jour, seulement des trades validés, avec un fort taux de réussite | Consigne donnée au chercheur : augmenter la réussite ET le gain moyen, jamais l'un sans l'autre | ✅ |
| Backtester sur tout l'historique, pas seulement le Bitcoin | 226 variantes testées sur 30 cryptos et 6 ans + une stratégie de rotation | ✅ `docs/recherche/2026-10-18.md` |

## Ce qui tourne tout seul, même conversation fermée

| Quoi | Quand |
|---|---|
| Trading réel (BTC, ETH, SOL) | Chaque jour à 02:25 (Paris) |
| Trading fictif (pour comparer) | Chaque jour à 02:20 |
| Stops et objectifs | En permanence, sur Hyperliquid |
| Notifications | À chaque événement |
| Recherche d'amélioration | Chaque dimanche à 7h47 |

## Ce qu'il faut savoir honnêtement

1. **La stratégie a un avantage faible.** Sur BTC/ETH/SOL depuis 2021 : environ +0,15 R par trade
   (+0,30 € par trade en moyenne avec 2 € de risque), avec des années négatives (2024, 2025).
   Il faudra plusieurs mois pour juger les résultats réels.
2. **Les trades sont rares** : quelques-uns par mois au maximum. C'est voulu.
3. **Les recherches d'aujourd'hui n'ont rien trouvé de mieux** qui tienne sur des données jamais vues :
   - élargir aux altcoins n'apporte rien (espérance ≈ 0) ;
   - les filtres qui augmentaient le taux de réussite sur le passé ne tiennent pas ensuite ;
   - la rotation sur les cryptos les plus fortes est une piste intéressante, mais avec des baisses de
     50 à 88 % et un biais du survivant à corriger.
4. **Les projets « ×10 / ×100 » (comme ASTER)** paraissent évidents après coup. Pour un ASTER, des
   centaines de projets aussi médiatisés ont fini à zéro. C'est le biais rétrospectif.
5. **Avec 25 €, le but est d'apprendre, pas de s'enrichir.** Les frais et le minimum de 10 $ par ordre
   pèsent beaucoup sur un si petit capital.

## Avant d'ajouter votre argent personnel

Je recommande d'attendre **au moins 20 à 30 trades réels** (plusieurs mois) et de vérifier que :
- les résultats réels ressemblent aux backtests ;
- aucune erreur d'exécution n'a eu lieu ;
- la plus forte baisse est restée supportable pour vous.

Ensuite, on augmente le capital **progressivement** en gardant 1 à 2 % de risque par trade, jamais plus.
Ne mettez jamais d'argent dont vous avez besoin.

## Pour tout arrêter

Supprimez la clé API « Claude code » sur **app.hyperliquid.xyz/API** : plus aucun ordre n'est possible,
immédiatement.
