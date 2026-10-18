# La stratégie de l'agent, expliquée simplement

## L'idée en une phrase

**On suit les grosses tendances du marché : on achète quand le prix casse un nouveau plus haut,
on vend à découvert quand il casse un nouveau plus bas, on coupe vite les perdants et on laisse
courir les gagnants.**

C'est la méthode des **Turtles** de Richard Dennis (1983), proche de ce que font Ed Seykota,
Paul Tudor Jones et les grands fonds de suivi de tendance. C'est l'une des rares stratégies dont
l'efficacité est documentée sur plus d'un siècle de données (Hurst, Ooi & Pedersen, 2017).

Elle tourne sur **BTC, ETH et SOL**, contrats perpétuels sur Hyperliquid, en **bougies journalières** :
l'agent prend ses décisions une fois par jour, juste après la clôture de la bougie (00:00 UTC).

---

## 1. Quand entrer ?

Les quatre conditions doivent être réunies en même temps :

| # | Condition pour un achat (long) | Pourquoi |
|---|---|---|
| 1 | Le prix de clôture dépasse **le plus haut des 20 derniers jours** | C'est le signal : le marché sort de sa zone et une tendance démarre peut-être. |
| 2 | Le prix est **au-dessus de sa moyenne mobile 200 jours** | Filtre de Paul Tudor Jones : on n'achète pas dans un marché baissier de fond. |
| 3 | L'**ADX est supérieur à 20** | L'ADX mesure la force d'une tendance. En dessous de 20, le marché tourne en rond et les cassures sont souvent fausses. |
| 4 | Le **funding n'est pas extrême** (< 0,01 %/h) | Si tout le monde est déjà acheteur avec du levier, le risque de « long squeeze » est élevé. |

Pour une **vente à découvert (short)**, c'est le miroir : cassure du plus bas des 20 jours, prix sous la MM200,
ADX > 20 et funding pas extrêmement négatif.

## 2. Où placer le stop ?

**Stop = prix d'entrée − 2 × ATR** (pour un long).

L'ATR (*Average True Range*) mesure de combien le prix bouge en moyenne chaque jour. Mettre le stop
à deux ATR, c'est le placer **assez loin pour ne pas sauter sur le bruit normal**, mais assez près
pour limiter la perte si la cassure était fausse. Le stop s'adapte tout seul à la volatilité :
plus large quand le marché est agité, plus serré quand il est calme.

## 3. Combien miser ? (le point le plus important)

On ne choisit **pas** un montant : on choisit **combien on accepte de perdre**, soit **1 % du capital**.

```
Taille de la position = (1 % du capital) ÷ (distance entre l'entrée et le stop)
```

Exemple avec 1 000 $ de capital : on risque 10 $. BTC est à 82 000 $ et le stop à 79 000 $
(3 000 $ d'écart). Taille = 10 ÷ 3 000 = 0,0033 BTC, soit environ 273 $ de position.
Si le stop est touché, on perd 10 $ (plus les frais), jamais plus.

Résultat : **10 pertes d'affilée ne coûtent qu'environ 10 % du capital**. C'est ce qui permet de
survivre aux longues séries de petits échecs, inévitables en suivi de tendance.

## 4. Comment sortir ?

| Situation | Action |
|---|---|
| Le prix touche le stop | Sortie : perte d'environ 1 R (1 R = le risque initial, ici 1 % du capital). |
| Le prix gagne **+1 R** | Le stop remonte au **prix d'entrée** : le trade ne peut plus perdre. |
| Le prix gagne **+2 R** | Le stop suit **le plus bas des 10 derniers jours** : on laisse courir et on sort quand la tendance s'essouffle. |
| Le prix atteint **+4 ATR** (≈ +2 R) | Prise de profit sur l'objectif. |

## 5. Les garde-fous (gestionnaire de risque)

Ces règles sont dans le code. Ni la stratégie ni l'IA ne peuvent les contourner :

- **1 %** de risque par trade, **3 %** au total sur toutes les positions ouvertes.
- BTC, ETH et SOL bougent ensemble, donc ils comptent comme **un seul pari** : **2 %** de risque maximum dans le même sens.
- **Levier effectif plafonné à 3x**, même si Hyperliquid autorise 40x.
- **−3 % dans la journée** : plus aucun nouveau trade avant le lendemain.
- **−10 % depuis le plus haut** : la taille des positions est divisée par deux.
- **−15 % depuis le plus haut** : **arrêt complet**, revue humaine obligatoire.

## 6. Le rôle de l'IA (analyste Claude)

Quand la stratégie produit un signal, Claude fait des recherches sur le web avant l'ouverture de la position.
Il cherche une annonce macro dans les 24 heures (Fed, inflation, emploi), un piratage, un procès,
un déblocage massif de tokens, etc. **Il peut seulement dire non** : il n'invente jamais de trade et ne change
ni la taille ni le stop. Ce choix vient des compétitions d'IA (Alpha Arena) : les modèles qui tradaient
librement ont perdu jusqu'à 63 %.

L'analyste est actif seulement si une clé `ANTHROPIC_API_KEY` est configurée. Sans elle,
le signal mécanique passe seul.

---

## 7. Pourquoi ces choix ? Ce que disent les tests

Tests sur Hyperliquid, BTC + ETH + SOL, août 2020 à octobre 2026, bougies journalières, frais
et slippage inclus, funding non compté :

| Variante | Trades | Réussite | Espérance | Rendement total | Baisse max |
|---|---|---|---|---|---|
| Cassure 20 jours + pullback | 168 | 33 % | +0,19 R | +34 % | 13,6 % |
| **Cassure 20 jours seule (retenue)** | **99** | **38 %** | **+0,29 R** | **+32 %** | **10,9 %** |
| Cassure 55 jours seule | 73 | 41 % | +0,39 R | +32 % | 9,1 % |

Sur 10 cryptos au lieu de 3, la stratégie de pullback seule ne gagne rien (+0,005 R par trade),
alors que la cassure seule reste positive (+0,11 R). Le pullback a donc été **désactivé**.
Les cassures sur 20 et 55 jours sont toutes les deux positives : c'est bon signe, la stratégie
ne dépend pas d'un réglage précis.

**Test « walk-forward » (hors échantillon) :** on choisit les meilleurs paramètres sur une année,
on les teste sur les 3 mois suivants jamais vus, et on recommence sur toute la période.
Résultat : **optimiser les paramètres n'apporte rien** (+0,07 R contre +0,09 R avec les réglages
par défaut). Les réglages classiques des Turtles sont donc gardés, sans ajustement.

### Ce qu'il faut savoir honnêtement

- **L'avantage est réel mais modeste** : environ +32 % en 6 ans avec 1 % de risque par trade,
  soit environ 5 % par an. **Garder du BTC sans rien faire a rapporté bien plus** sur la même
  période (BTC est passé d'environ 12 000 $ à 82 000 $). L'intérêt de la stratégie est de
  **limiter les pertes** (baisse maximale d'environ 11 % contre plus de 75 % pour le BTC en 2022)
  et de gagner aussi quand le marché baisse.
- Avec seulement 3 actifs très corrélés, la diversification est faible. Les fonds de suivi de tendance
  tradent 50 à 100 marchés différents.
- Le taux de réussite d'environ 38 % implique **de longues séries de pertes**. C'est normal.
- 99 trades en 6 ans, c'est peu : il faudra **beaucoup de temps** pour confirmer en réel.
- Le funding n'est pas compté dans les tests. Il coûte en général un peu aux positions acheteuses.

## 8. Les étapes

1. **Paper trading quotidien et automatique** (GitHub Actions, chaque jour à 00:20 UTC) : **en cours**.
2. Après 4 à 8 semaines, comparaison des résultats fictifs avec les backtests.
3. Si c'est cohérent : petit capital réel, avec validation manuelle de chaque trade au début.
