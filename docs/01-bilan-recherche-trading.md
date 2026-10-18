# Bilan de recherche : comment pensent et opèrent les grands traders

> Base de connaissances pour concevoir un agent de trading autonome.
> Rédigé le 18/10/2026. Ce document n'est pas un conseil en investissement.

---

## 0. Commencer par la réalité chiffrée

Avant d'étudier les gagnants, il faut regarder la base statistique, parce que l'agent devra battre ces chiffres.

| Étude / source | Constat |
|---|---|
| Chague, De-Losso & Giovannetti (2019), day traders brésiliens sur contrats à terme | **97 %** de ceux qui ont persisté plus de 300 jours ont perdu de l'argent ; seuls **1,1 %** ont gagné plus que le salaire minimum. |
| Barber, Lee, Liu & Odean (Taïwan, 1992-2006) | **Moins de 1 %** des day traders sont rentables de façon prévisible d'une année sur l'autre. |
| Avertissements obligatoires ESMA (CFD, Europe) | En général **70 à 80 %** des comptes particuliers perdent de l'argent. |
| Alpha Arena, saison 1 (nof1.ai, fin 2025) : 6 LLM, 10 000 $ chacun, perpétuels sur Hyperliquid | Qwen3-Max **+22 %**, DeepSeek **+5 %**, Claude Sonnet 4.5 **−31 %**, Grok 4 **−45 %**, Gemini 2.5 Pro **−57 %**, GPT-5 **−63 %**. Les leaders de la première semaine n'étaient plus les mêmes à la fin. |
| Benchmark AI-Trader (fin 2025) | La plupart des agents ont de mauvais résultats. GPT-5 fait +1,56 % contre +1,87 % pour le QQQ. Le meilleur (MiniMax-M2) l'a été grâce à **sa gestion du risque**, pas grâce à ses prédictions. |
| HKU Agentic Trader (forex, 2026) | Les écarts entre modèles se creusent quand l'agent doit s'adapter en temps réel. |

**Ce qu'il faut en retenir pour l'agent :**
1. Le marché est un jeu à somme négative une fois les frais, le spread, le slippage et le funding déduits.
2. Un LLM qui « analyse comme un expert » ne gagne pas d'argent par défaut. Ce qui distingue les survivants, c'est le **contrôle du risque**, pas la qualité de la prédiction.
3. Les performances sur quelques semaines sont surtout du bruit. Il faut des centaines de trades pour juger un système.

---

## 1. Fiches des grands traders

### 1.1 Spéculateurs discrétionnaires et macro

**Jesse Livermore (1877-1940)** : le spéculateur de référence (*Reminiscences of a Stock Operator*).
- Il trade la **tendance générale** du marché, pas les fluctuations. Selon lui, « ce n'est pas en réfléchissant que j'ai gagné beaucoup, c'est en restant assis. »
- Il achète sur les **points pivots** : cassure d'un niveau clé avec du volume, à des prix nouveaux.
- **Pyramidage** : il n'ajoute à une position que si elle est déjà gagnante, jamais à une perdante.
- Il coupe vite les pertes, autour de 10 % au maximum.
- Il a fait faillite plusieurs fois, en violant ses propres règles. Leçon : la discipline compte plus que l'intelligence.

**Paul Tudor Jones** (Tudor Investment, a prévu le krach de 1987)
- « La chose la plus importante, c'est de jouer une excellente défense, pas une excellente attaque. »
- Il vise un ratio gain/risque d'**au moins 5:1**. À ce ratio, on peut avoir tort 80 % du temps sans perdre d'argent.
- Il utilise la **moyenne mobile 200 jours** comme filtre absolu : « rien de bon ne se passe sous la 200 jours ».
- Il réduit la taille de ses positions quand il est en drawdown et l'augmente quand il gagne.
- Il raisonne par **analogie historique** (le graphique de 1987 superposé à celui de 1929).

**George Soros** (Quantum Fund, short de la livre sterling en 1992, environ 1 milliard $ de gain)
- **Réflexivité** : les perceptions des acteurs modifient les fondamentaux, qui modifient en retour les perceptions. Les bulles se nourrissent d'elles-mêmes jusqu'à la rupture.
- Il cherche les **déséquilibres insoutenables** (taux de change fixes, politiques incohérentes).
- « Ce qui compte, ce n'est pas d'avoir raison ou tort, c'est combien on gagne quand on a raison et combien on perd quand on a tort. »
- Quand la conviction est maximale, il faut y aller fort (« il faut du courage pour être un porc »).

**Stanley Druckenmiller** (gérant chez Soros, environ 30 % par an sur 30 ans sans année négative)
- Les **liquidités et les banques centrales** font bouger les marchés, pas les bénéfices. Il suit la Fed, les taux et la liquidité.
- Il regarde **18 à 24 mois en avant** : le marché anticipe.
- Concentration : très peu de positions, mais grosses quand le setup est exceptionnel.
- Il protège d'abord le capital, puis attaque quand l'opportunité est asymétrique.
- Il est capable de **changer d'avis instantanément** sans ego.

**Bruce Kovner** (Caxton, macro)
- Il place son stop à un niveau où le marché lui prouverait qu'il a tort, **pas** à un niveau défini par le montant qu'il accepte de perdre. Ensuite il ajuste la taille de la position à ce stop.
- Il ne risque jamais plus de 1 à 2 % du capital par idée.

**Ray Dalio** (Bridgewater)
- Le marché est une **machine** à comprendre : cycles de dette courts et longs, croissance et inflation.
- **All Weather / parité de risque** : on équilibre le risque, pas les montants, entre actifs décorrélés.
- « Le Graal de l'investissement » : **15 flux de revenus non corrélés** réduisent le risque d'environ 80 % sans réduire le rendement attendu.
- Principes écrits et systématisés, chaque erreur devient une règle.

**Jim Rogers** : macro sur les matières premières, horizon long, il cherche les marchés « où rien ne se passe » avant un catalyseur.

**Michael Burry / John Paulson** (subprimes, 2007) : thèses fondamentales profondes, achat d'**assurances asymétriques** (CDS) à coût limité et à gain potentiel énorme. Il faut avoir la patience de tenir pendant que le marché pense que vous avez tort.

### 1.2 Suiveurs de tendance et systématiques

**Ed Seykota** : pionnier des systèmes informatisés (années 1970).
- Ses règles : (1) couper les pertes, (2) laisser courir les gains, (3) garder les positions petites, (4) suivre les règles sans poser de questions, (5) savoir quand les enfreindre.
- « Tout le monde obtient ce qu'il veut du marché » : la psychologie du trader détermine ses résultats.
- « The trend is your friend except at the end where it bends. »

**Richard Dennis & les Turtles** (1983) : l'expérience qui montre que le trading **s'enseigne**.
- **Entrée** : cassure du plus haut ou du plus bas sur 20 jours (système 1) ou 55 jours (système 2).
- **Sortie** : cassure inverse sur 10 jours (S1) ou 20 jours (S2).
- **Stop** : 2 × ATR (N).
- **Taille** : 1 unité = 1 % du capital ÷ (N × valeur du point). Maximum 4 unités par marché, 12 sur des marchés corrélés.
- **Pyramidage** : ajout d'une unité tous les +0,5 N.
- Taux de réussite d'environ 35 à 40 %, la rentabilité vient des grosses tendances.
- La plupart des élèves ont échoué non pas à cause du système mais parce qu'ils n'ont **pas suivi les règles**.

**Larry Hite** (Mint) : « Si tu ne mises pas, tu ne peux pas gagner. Si tu perds tous tes jetons, tu ne peux pas miser. » Il risque 1 % par trade.

**Tom Basso** : « Mr. Serenity ». Pour lui, la gestion de la taille de position et la psychologie importent bien plus que les points d'entrée. Il a montré que des entrées **aléatoires** combinées à une bonne gestion du risque peuvent être rentables.

**Jim Simons** (Renaissance Technologies, Medallion : environ 66 % brut par an de 1988 à 2018)
- Uniquement des données, aucune intuition. Il recrute des mathématiciens, physiciens et linguistes, pas des financiers.
- Il cherche des **signaux faibles et non intuitifs** (taux de réussite d'environ 50,75 %), mais sur des millions de trades avec un fort levier.
- Le fonds a une capacité limitée et rend l'argent des investisseurs extérieurs : les edges se dégradent avec la taille.
- **Leçon pour l'agent** : un edge minuscule exploité à grande échelle avec une exécution parfaite bat une prédiction spectaculaire.

**Ken Griffin (Citadel), Steve Cohen (Point72)** : plateformes multi-gérants. Chaque gérant a des **limites de drawdown dures** (souvent −5 % : allocation réduite de moitié, −7,5 % ou −10 % : sortie). Le risque est **géré par une couche indépendante** du gérant. C'est le modèle à reproduire dans l'agent.

### 1.3 Swing traders et momentum sur les actions

**William O'Neil** (CAN SLIM, *Investor's Business Daily*)
- **C**urrent earnings (bénéfice du trimestre en forte hausse), **A**nnual earnings, **N**ew (nouveau produit ou nouveau plus haut), **S**upply/demand (volume), **L**eader vs laggard, **I**nstitutional sponsorship, **M**arket direction.
- Il achète la cassure d'une **base** (tasse avec anse) et vend **sans exception** à −7 / −8 %.
- 3 actions sur 4 suivent la direction du marché, donc il ne trade pas contre le marché.

**Mark Minervini** (champion US Investing 1997, +220 %)
- **Trend Template** : cours > MM50 > MM150 > MM200, MM200 en hausse depuis au moins 1 mois, cours à plus de 30 % au-dessus du plus bas sur 52 semaines et à moins de 25 % du plus haut.
- **VCP** (Volatility Contraction Pattern) : des contractions de plus en plus serrées avec un volume qui s'assèche, puis une cassure.
- Stop moyen de 5 à 6 %, perte maximale de 10 %. Il ne laisse jamais un gain important redevenir une perte.

**Nicolas Darvas** : la **théorie des boîtes**. Il achète la cassure du haut de la boîte avec du volume et remonte son stop sous chaque nouvelle boîte.

**Linda Raschke** : swing et court terme. Elle utilise des setups simples et répétables (« Holy Grail » : pullback vers la MM20 quand l'ADX est supérieur à 30, « Turtle Soup » : faux breakouts), un journal minutieux et la règle de ne jamais transformer un trade court terme en investissement.

**Peter Brandt** : figures chartistes classiques. Il ne prend que les meilleures, environ **1 sur 10**. Il risque moins de 1 % par trade, accepte un taux de réussite d'environ 40 %, et dit que la plupart de ses profits viennent de 10 % de ses trades.

**Larry Williams** (Coupe du monde 1987 : +11 376 %) : saisonnalité, indicateurs du COT (positions des commerciaux), %R de Williams. Il souligne que son record a été obtenu avec un levier qui aurait aussi pu le ruiner.

**Alexander Elder** : « 3M » (Mind, Method, Money). **Triple Screen** : tendance en hebdomadaire, oscillateur en journalier, entrée en intraday. **Règle des 2 %** par trade et **règle des 6 %** : on arrête de trader le mois si le capital a perdu 6 %.

**Van Tharp** : **R-multiples** et **expectancy** (voir section 4). Il estime que la taille de position explique plus de 90 % de la variabilité des performances.

### 1.4 Crypto

**Arthur Hayes** (fondateur de BitMEX) : macro de la liquidité en dollars. Il regarde le bilan de la Fed, le TGA (compte du Trésor) et les reverse repos. Le bitcoin est pour lui un « détecteur de fumée » de la liquidité fiat.

**GCR** (trader pseudonyme) : contrarien sur le sentiment. Il est connu pour son pari public contre Do Kwon (short de LUNA avant l'effondrement de 2022). Il shorte l'euphorie, achète la capitulation et fait des paris rares mais concentrés.

**Pratiques communes chez les traders crypto discrétionnaires reconnus** :
- Lire le **funding rate**, l'**open interest** et les **zones de liquidation**. Quand le funding est très positif et que l'OI monte pendant que le prix stagne, la foule est en levier long et risque un « long squeeze ».
- Suivre la dominance BTC et les rotations BTC → ETH → grosses alts → petites alts.
- Surveiller les débloquages de tokens (unlocks), les flux vers les exchanges et l'offre de stablecoins.
- Partir du principe que l'essentiel des alts finit à −90 % : prendre ses profits.

---

## 2. Les points communs (synthèse de *Market Wizards* de Jack Schwager)

Schwager a interviewé plus de 50 traders d'élite. Ses conclusions transversales :

1. **Il n'existe pas de méthode unique**. Certains sont fondamentaux, d'autres techniques, d'autres quantitatifs. Chacun a trouvé une méthode qui **convient à sa personnalité** et ne s'en écarte pas.
2. **Edge identifié** : chacun sait précisément *pourquoi* il gagne de l'argent.
3. **Gestion du risque obsessionnelle** : tous coupent leurs pertes, risquent une petite fraction du capital par trade et ont une limite de perte maximale.
4. **Asymétrie** : des pertes petites et nombreuses, quelques gains énormes. Un taux de réussite de 30 à 50 % est **normal**.
5. **Discipline** : les règles s'appliquent même après 5 pertes d'affilée.
6. **Patience** : attendre le setup « A+ », ne rien faire la plupart du temps.
7. **Indépendance** : penser contre le consensus quand les données le justifient.
8. **Flexibilité** : changer d'avis sans ego, et ne jamais « épouser » une position.
9. **Réduire la taille en drawdown**, ne pas « se refaire ».
10. **Responsabilité** : les pertes sont la faute du trader, jamais celle du marché.
11. **Travail** : revue quotidienne, journal, analyse post-mortem.
12. **Les échecs initiaux** : la plupart ont perdu plusieurs comptes avant de réussir. L'expérience de la perte construit la discipline.

---

## 3. Les méthodes d'analyse

### 3.1 Analyse technique (la plus automatisable)

| Famille | Outils | Usage par les pros |
|---|---|---|
| **Tendance** | MM 20/50/200, EMA, ADX, Ichimoku, plus hauts et plus bas successifs | Définir le *régime* : ne trader que dans le sens de la tendance de fond. |
| **Momentum** | RSI, MACD, stochastique, ROC | Les divergences RSI et prix signalent un essoufflement. RSI > 70 en tendance forte = force, pas forcément un signal de vente. |
| **Volatilité** | ATR, Bollinger, Keltner, volatilité historique et implicite | Calibrer les stops et la taille. Une compression de volatilité (squeeze) précède souvent l'expansion. |
| **Volume** | OBV, VWAP, profil de volume (POC, value area), CVD | Une cassure sans volume est suspecte. Le VWAP sert de référence institutionnelle intraday. |
| **Structure** | Supports et résistances, figures (tête-épaules, triangles, drapeaux, tasse avec anse), breakouts, pullbacks | Placer les entrées et les stops sur des niveaux objectifs. |
| **Multi-timeframe** | Triple Screen d'Elder | La tendance en H4 ou D1, le signal en H1, le timing en M15. |
| **Price action / SMC** | Order blocks, fair value gaps, liquidity sweeps, BOS/CHoCH | Populaires en crypto. L'efficacité statistique est peu prouvée, à valider par backtest. |

### 3.2 Analyse fondamentale
- **Actions** : croissance du BPA et du chiffre d'affaires, marges, ROE, valorisation (PER, EV/EBITDA, FCF yield), révisions des analystes, surprises de résultats (le *post-earnings announcement drift* est une anomalie documentée).
- **Crypto (« tokenomics »)** : offre en circulation vs offre totale (FDV), calendrier des unlocks, revenus réels du protocole, TVL, utilisateurs actifs, distribution des holders, émissions et inflation.

### 3.3 Macro
- La politique monétaire (taux, QE/QT, bilan des banques centrales) et la **liquidité nette** (bilan Fed − TGA − RRP).
- Le dollar (DXY) et les taux réels : un dollar fort pèse sur les actifs risqués et sur la crypto.
- Le calendrier : CPI, NFP, FOMC, PCE. La volatilité augmente autour de ces publications. L'agent doit **réduire son exposition ou s'abstenir** autour d'elles.
- Les corrélations : le BTC est souvent corrélé au Nasdaq en période de stress.

### 3.4 Sentiment et positionnement
- Fear & Greed Index, put/call ratio, VIX, rapport COT (CFTC), enquêtes AAII.
- Crypto : **funding rates**, **open interest**, ratio long/short, **heatmaps de liquidations**, basis futures, skew des options (Deribit).
- Réseaux sociaux : le volume de mentions est un indicateur **contrarien** aux extrêmes.

### 3.5 Données on-chain (spécifique à la crypto)
- **MVRV, NUPL, SOPR** : profit ou perte latents des détenteurs, utiles pour identifier les extrêmes de cycle.
- **Flux entrants et sortants des exchanges** : des entrées massives annoncent une pression vendeuse potentielle.
- **Offre de stablecoins** (USDT/USDC mint) : de la « poudre sèche » prête à acheter.
- **Wallets de baleines et de smart money** (Nansen, Arkham) : copier avec prudence, les données sont bruitées.
- **Coût de production des mineurs**, hashrate.

### 3.6 Approche quantitative
- **Facteurs** documentés académiquement : momentum (12-1 mois), value, qualité, faible volatilité, carry. **Le momentum croisé et le time-series momentum** (trend following) sont les plus robustes sur un siècle de données (Moskowitz, Ooi, Pedersen 2012 ; Hurst, Ooi, Pedersen « A Century of Evidence on Trend-Following »).
- **Mean reversion** : fonctionne en intraday et sur des paires cointégrées, échoue en tendance forte.
- **Arbitrage statistique, market making** : un edge petit mais régulier, qui demande une infrastructure à faible latence. Peu adapté à un agent LLM.
- **Détection de régime** : volatilité haute ou basse, tendance ou range (HMM, seuils ADX/ATR). Les meilleurs systèmes **changent de stratégie selon le régime**.

---

## 4. Gestion du risque : le cœur du système

### 4.1 Formules essentielles

**Taille de position (risque fixe, méthode Kovner, Turtles, Elder)**
```
Risque_$ = Capital × %risque         (1 % recommandé, 2 % au maximum)
Taille   = Risque_$ / |Entrée − Stop|
```
Exemple : capital de 10 000 $, risque de 1 % = 100 $. Entrée BTC à 60 000, stop à 58 800 (écart de 1 200). Taille = 100 / 1 200 = 0,0833 BTC (≈ 5 000 $ notionnels).

**Stop basé sur la volatilité** : `Stop = Entrée − k × ATR(14)`, avec k entre 1,5 et 3.

**R-multiple (Van Tharp)** : `R = (Sortie − Entrée) / (Entrée − Stop)`. Chaque trade s'exprime en multiples du risque initial.

**Espérance (expectancy)**
```
E = (Taux_gain × Gain_moyen) − (Taux_perte × Perte_moyenne)
```
Avec 40 % de gains à +2,5 R et 60 % de pertes à −1 R : E = 1,0 − 0,6 = **+0,4 R par trade**.

**Critère de Kelly** : `f* = p − (1 − p) / b` (p = probabilité de gain, b = gain/perte). Les pros utilisent **¼ à ½ Kelly** au maximum, parce que le Kelly complet produit des drawdowns insupportables et que p est toujours surestimé.

**Mathématiques du drawdown** (pourquoi la défense prime)

| Perte | Gain nécessaire pour revenir |
|---|---|
| −10 % | +11 % |
| −20 % | +25 % |
| −30 % | +43 % |
| −50 % | +100 % |
| −75 % | +300 % |

### 4.2 Règles de risque à coder en dur (non négociables pour l'agent)
1. Risque par trade **≤ 1 %** du capital.
2. Un **stop obligatoire** placé au moment de l'entrée, jamais élargi.
3. Exposition totale (somme des risques ouverts) **≤ 5 %**.
4. Limite sur les positions corrélées (par exemple, BTC + ETH + SOL long = un seul pari).
5. **Perte journalière maximale de 3 %** : l'agent s'arrête jusqu'au lendemain.
6. **Drawdown maximal de 10 %** depuis le plus haut : taille divisée par 2. **À 15 %, arrêt complet** et revue humaine (modèle Citadel/Point72).
7. Levier effectif plafonné, par exemple à 3x, même si l'exchange autorise 50x.
8. Pas de « moyenne à la baisse » sur une position perdante.
9. Pas de trade dans les 30 minutes qui entourent une annonce macro majeure.
10. Un **kill switch** manuel accessible à tout moment.

---

## 5. Psychologie et biais (ce qu'un agent peut éviter, s'il est bien conçu)

| Biais | Effet chez l'humain | Risque spécifique d'un agent LLM |
|---|---|---|
| Aversion à la perte / effet de disposition | Vendre les gagnants trop tôt, garder les perdants | Le LLM « rationalise » une position perdante avec un nouveau narratif. |
| Revenge trading | Surtrader après une perte | Une boucle qui relance des trades sans cooldown. |
| Excès de confiance | Trop de levier après une série de gains | Les LLM sont mal calibrés et expriment une forte certitude même quand ils se trompent. |
| Biais de confirmation | Ne voir que ce qui confirme la thèse | Le prompt oriente la conclusion. |
| Récence | Extrapoler les dernières bougies | Une fenêtre de contexte limitée aux données récentes. |
| FOMO | Acheter le sommet après un pump | Réagir aux news virales. |
| Hallucination | — | Inventer des prix, niveaux ou news. **Les données chiffrées doivent toujours venir d'API, jamais du modèle.** |

Le principal avantage d'un agent : il ne connaît **ni la peur ni la fatigue**, à condition que les règles soient appliquées par du **code déterministe** et pas laissées à la discrétion du LLM.

---

## 6. Processus quotidien des pros (à reproduire)

1. **Pré-marché** : contexte macro, calendrier, régime de marché, niveaux clés, watchlist.
2. **Plan de trade écrit avant l'entrée** : thèse, setup, entrée, stop, objectifs, taille, invalidation, R:R ≥ 2.
3. **Exécution** : ordres limites de préférence, attention au slippage et aux frais.
4. **Gestion** : stop au breakeven après +1 R, sorties partielles, trailing stop (ATR ou MM).
5. **Journal** : chaque trade avec capture, raison, émotion (pour l'humain) ou raisonnement (pour l'agent), résultat en R.
6. **Revue hebdomadaire** : statistiques par setup (win rate, R moyen, expectancy, profit factor, max DD, Sharpe/Sortino). On **supprime les setups qui ne marchent pas**.

---

## 7. Ce que les compétitions d'IA nous apprennent

- **La variance est énorme** : à Alpha Arena, les classements de la semaine 1 se sont inversés à la fin. Quelques semaines ne prouvent rien.
- **Les perdants surtradaient** avec beaucoup de levier, et les gagnants tradaient peu (Qwen3-Max : 43 trades, 30 % de réussite, mais une asymétrie favorable).
- **La gestion du risque explique les différences** (AI-Trader : MiniMax-M2 l'emporte par sa prudence).
- Les LLM sont **sensibles au prompt** et à l'ordre des données, et leurs décisions sont peu reproductibles.
- **Conclusion de conception** : le LLM ne doit pas être le « trader » libre. Il doit être un **analyste** qui propose, encadré par du code qui vérifie, dimensionne et exécute.

---

## 8. Traduction en architecture d'agent

```
┌──────────────────────────────────────────────────────────────┐
│ 1. DONNÉES (déterministe)                                     │
│    Prix OHLCV, carnet, funding, OI, on-chain, calendrier      │
│    macro, news. Sources API vérifiées, aucun chiffre inventé. │
├──────────────────────────────────────────────────────────────┤
│ 2. SIGNAUX QUANT (code)                                       │
│    Régime (tendance/range, vol), trend template, breakouts    │
│    Donchian, RSI, ATR, funding extrême… Score par stratégie.  │
├──────────────────────────────────────────────────────────────┤
│ 3. ANALYSTE LLM (Claude)                                      │
│    Synthèse multi-sources, lecture des news et du contexte,   │
│    rédaction d'un plan de trade structuré (JSON) ou « PASS ». │
│    Peut seulement PROPOSER.                                   │
├──────────────────────────────────────────────────────────────┤
│ 4. RISK MANAGER (code, droit de veto absolu)                  │
│    Règles 4.2, calcul de la taille, vérif. corrélation,       │
│    limites journalières et drawdown, kill switch.             │
├──────────────────────────────────────────────────────────────┤
│ 5. EXÉCUTION (code)                                           │
│    Ordres limites, stop placé immédiatement, gestion du       │
│    slippage et du gas, simulation de la transaction avant.    │
├──────────────────────────────────────────────────────────────┤
│ 6. JOURNAL & REVUE                                            │
│    Base de données des trades, métriques, rapport hebdo,      │
│    alertes (Telegram/e-mail).                                 │
└──────────────────────────────────────────────────────────────┘
```

**Stratégies candidates de départ** (les plus robustes selon la littérature) :
1. **Suivi de tendance multi-actifs** façon Turtles : cassure de Donchian 20/55 avec un stop à 2 ATR, filtre MM200.
2. **Momentum en pullback** : tendance confirmée (trend template) + retour sur la MM20/EMA21 + reprise.
3. **Contrarien sur le positionnement** (crypto) : funding extrême + OI élevé + divergence de prix → trade contre la foule, avec petite taille.
4. **Filtre de régime** : pas de trade en tendance si l'ADX < 20, pas de mean reversion si l'ADX > 30.

**Pièges du backtest à éviter** : sur-optimisation (curve fitting), biais d'anticipation (look-ahead), biais du survivant (tokens disparus), oubli des frais, du slippage et du funding, et absence de validation hors échantillon (*walk-forward*). Une stratégie doit fonctionner avec des paramètres « ronds » et voisins, sinon elle est sur-ajustée.

**Feuille de route recommandée :**
1. Backtest des stratégies sur 3 ans ou plus de données, frais compris.
2. **Paper trading** de 4 à 8 semaines en conditions réelles (sans argent).
3. Live avec un **petit capital** (une somme que l'on accepte de perdre entièrement), en semi-automatique : l'agent propose et vous validez d'un clic.
4. Autonomie progressive, uniquement si les métriques live correspondent au backtest.

---

## 9. Connexion au wallet (MetaMask) : sécurité d'abord

**Règles absolues :**
- **Ne jamais donner votre phrase de récupération (seed phrase) ni votre clé privée principale**, à moi, à une application ou à un script. Quiconque l'a peut vider le wallet de façon irréversible.
- Utiliser un **wallet dédié au trading**, séparé de votre wallet principal, alimenté uniquement avec le capital alloué à l'agent.

**Options techniques, de la plus sûre à la moins sûre :**

1. **Permissions limitées MetaMask (ERC-7715, « Advanced Permissions »)** : MetaMask (Smart Accounts Kit, v13.23 ou plus) permet de donner à une application une permission **bornée** via `wallet_grantPermissions`, par exemple « dépenser au maximum X USDC par jour ». L'agent utilise une clé de session qui ne détient aucun fonds et ne peut agir que dans ce périmètre. Révocable à tout moment.
2. **Wallet API / agent sur un DEX de perpétuels (par exemple Hyperliquid)** : vous connectez MetaMask une fois, puis vous autorisez une « API wallet » qui peut **trader mais pas retirer**. Le risque est limité au trading lui-même. C'est l'infrastructure utilisée par Alpha Arena.
3. **Mode semi-automatique** : l'agent prépare la transaction et vous la signez dans MetaMask. C'est le plus sûr pour démarrer.
4. Clé privée d'un hot wallet dédié stockée dans un gestionnaire de secrets : acceptable seulement pour un petit montant, avec des plafonds codés.

**Risques spécifiques on-chain** : MEV et sandwich attacks sur les DEX (utiliser une tolérance de slippage serrée et un RPC privé ou protégé), frais de gas, smart contracts frauduleux ou tokens piégés (honeypots). Il faut une **liste blanche** de contrats et tokens autorisés.

---

## 10. Bibliographie et sources

**Livres de référence**
- Jack Schwager, *Market Wizards*, *The New Market Wizards*, *Hedge Fund Market Wizards*, *Unknown Market Wizards*
- Edwin Lefèvre, *Reminiscences of a Stock Operator* (Livermore)
- Michael Covel, *The Complete TurtleTrader* ; Curtis Faith, *Way of the Turtle*
- Mark Minervini, *Trade Like a Stock Market Wizard*
- William O'Neil, *How to Make Money in Stocks*
- Van K. Tharp, *Trade Your Way to Financial Freedom*
- Alexander Elder, *Trading for a Living*
- George Soros, *The Alchemy of Finance*
- Ray Dalio, *Principles* et *Big Debt Crises*
- Gregory Zuckerman, *The Man Who Solved the Market* (Jim Simons)
- Mark Douglas, *Trading in the Zone*
- Nassim Taleb, *Fooled by Randomness*
- Ernest Chan, *Algorithmic Trading* ; Marcos López de Prado, *Advances in Financial Machine Learning*

**Études académiques**
- Chague, De-Losso, Giovannetti (2019), *Day Trading for a Living?*
- Barber, Lee, Liu, Odean, *The Cross-Section of Speculator Skill: Evidence from Day Trading*
- Moskowitz, Ooi, Pedersen (2012), *Time Series Momentum*
- Hurst, Ooi, Pedersen (2017), *A Century of Evidence on Trend-Following Investing*

**Agents IA et trading (2025-2026)**
- [When Agents Trade: Live Multi-Market Trading Benchmark for LLM Agents (arXiv 2510.11695)](https://arxiv.org/pdf/2510.11695)
- [What LLM Trading Agents Actually Do in Production (arXiv 2609.05663)](https://arxiv.org/pdf/2609.05663)
- [HKU Business School : AI Agents' Trading Performance](https://www.hkubs.hku.hk/media/press-release/testing-ai-in-the-real-world-hku-business-school-released-ai-agents-trading-performance/)
- [Alpha Arena : DeepSeek / Qwen (SCMP)](https://www.scmp.com/tech/tech-trends/article/3329784/deepseek-outperforms-ai-rivals-real-money-real-market-crypto-showdown)
- [Alpha Arena : analyse (Decrypt)](https://decrypt.co/es/345099/trading-cripto-con-ia-deepseek-y-grok-dominan-mientras-gemini-se-desmorona/)
- [Leçons d'Alpha Arena (Buildix)](https://www.buildix.trade/blog/nof1-alpha-arena-lessons-ai-trading-byok-strategy-advisor-2026)

**MetaMask et permissions déléguées**
- [MetaMask Smart Accounts Kit : Advanced Permissions (ERC-7715)](https://docs.metamask.io/smart-accounts-kit/concepts/advanced-permissions/)
- [MetaMask Delegation Toolkit : ERC-7715](https://docs.metamask.io/delegation-toolkit/concepts/erc7715)

> Remarque : les chiffres des compétitions d'IA proviennent en partie de sources secondaires. Les citations des traders sont des paraphrases fidèles de leurs livres et interviews.
