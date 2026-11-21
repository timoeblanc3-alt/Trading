"""Suivi des candidats de radar/historique.csv : performance depuis le signalement, comparée au BTC.

Usage : python3 radar/outils/suivi.py
Une ligne est une « réussite » si le candidat fait mieux que le BTC depuis son signalement
et n'est pas passé sous son niveau d'invalidation. Les signaux de moins de 7 jours sont
affichés mais exclus du taux de réussite.
"""
import csv
import datetime as dt
import json
import os
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def mids():
    req = urllib.request.Request("https://api.hyperliquid.xyz/info", data=b'{"type":"allMids"}',
                                 headers={"Content-Type": "application/json"})
    return {k: float(v) for k, v in json.loads(urllib.request.urlopen(req, timeout=20).read()).items()}


def btc_close_on(date):
    t = int(dt.datetime.fromisoformat(date).replace(tzinfo=dt.timezone.utc).timestamp() * 1000)
    body = json.dumps({"type": "candleSnapshot", "req": {"coin": "BTC", "interval": "1h",
                       "startTime": t, "endTime": t + 3_600_000}}).encode()
    req = urllib.request.Request("https://api.hyperliquid.xyz/info", data=body, headers={"Content-Type": "application/json"})
    rows = json.loads(urllib.request.urlopen(req, timeout=20).read())
    return float(rows[0]["o"]) if rows else None


def low_since(coin, when):
    """Plus bas atteint depuis le signalement (bougies 1 h) : l'invalidation compte même si le prix est remonté."""
    t = int(dt.datetime.fromisoformat(when).replace(tzinfo=dt.timezone.utc).timestamp() * 1000)
    body = json.dumps({"type": "candleSnapshot", "req": {"coin": coin, "interval": "1h", "startTime": t,
                       "endTime": int(dt.datetime.now(dt.timezone.utc).timestamp() * 1000)}}).encode()
    req = urllib.request.Request("https://api.hyperliquid.xyz/info", data=body, headers={"Content-Type": "application/json"})
    rows = json.loads(urllib.request.urlopen(req, timeout=20).read())
    return min((float(c["l"]) for c in rows), default=None)


def main():
    px = mids()
    today = dt.datetime.now(dt.timezone.utc)
    done, wins = 0, 0
    print(f"{'date':10} {'coin':6} {'note':>4} {'perf':>7} {'vs BTC':>7}  statut")
    for r in csv.DictReader(open(os.path.join(ROOT, "historique.csv"))):
        when = f"{r['date']}T{r['heure_utc']}:00"
        btc0 = btc_close_on(when)
        p = px.get(r["coin"])
        if not p or not btc0:
            continue
        perf = (p / float(r["prix"]) - 1) * 100
        rel = perf - (px["BTC"] / btc0 - 1) * 100
        age = max(0, (today - dt.datetime.fromisoformat(when).replace(tzinfo=dt.timezone.utc)).days)
        low = low_since(r["coin"], when)
        invalid = low is not None and low < float(r["invalidation"])
        ok = rel > 0 and not invalid
        status = "invalidé" if invalid else ("en avance" if rel > 0 else "en retard")
        if age >= 7:
            done += 1
            wins += ok
        else:
            status += f" (trop récent, {age} j)"
        print(f"{r['date']:10} {r['coin']:6} {r['note_sur_5']:>4} {perf:+6.1f}% {rel:+6.1f}%  {status}")
    print(f"\nTaux de réussite (signaux de 7 j et plus) : {wins}/{done}" if done else "\nPas encore de signal de 7 jours ou plus.")


if __name__ == "__main__":
    main()
