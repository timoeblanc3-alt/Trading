"""Scan quotidien de tous les perps Hyperliquid (lecture seule, API publique).

Usage : python3 radar/outils/scan.py [AAAA-MM-JJ]
Écrit radar/donnees/scan-AAAA-MM-JJ.csv (indicateurs) et radar/donnees/oi-AAAA-MM-JJ.csv
(relevé d'open interest, pour construire l'historique que l'API ne fournit pas).
"""
import csv
import datetime as dt
import json
import os
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

API = "https://api.hyperliquid.xyz/info"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DAY = 86_400_000


def post(payload, retries=4):
    data = json.dumps(payload).encode()
    for i in range(retries):
        try:
            req = urllib.request.Request(API, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except Exception:
            if i == retries - 1:
                raise
            time.sleep(2 ** i)


def daily(coin, days=1500):
    end = int(time.time() * 1000)
    rows = post({"type": "candleSnapshot", "req": {"coin": coin, "interval": "1d",
                                                   "startTime": end - days * DAY, "endTime": end}})
    return [(c["t"], float(c["h"]), float(c["l"]), float(c["c"]), float(c["v"]) * float(c["c"])) for c in rows or []]


def pct(a, b):
    return (a / b - 1) * 100 if b else None


def oi_history(today):
    """Relevés d'OI passés : {coin: [(date, oi_usd), ...]}."""
    hist = {}
    folder = os.path.join(ROOT, "donnees")
    for name in sorted(os.listdir(folder)):
        if name.startswith("oi-") and name.endswith(".csv") and name[3:13] < today:
            for row in csv.DictReader(open(os.path.join(folder, name))):
                hist.setdefault(row["coin"], []).append((name[3:13], float(row["oi_usd"])))
    return hist


def main():
    today = sys.argv[1] if len(sys.argv) > 1 else dt.date.today().isoformat()
    meta, ctxs = post({"type": "metaAndAssetCtxs"})
    assets = []
    for a, c in zip(meta["universe"], ctxs):
        if a.get("isDelisted"):
            continue
        mark = float(c["markPx"])
        assets.append({"coin": a["name"], "mark": mark, "funding_an": float(c["funding"]) * 24 * 365 * 100,
                       "oi_usd": float(c["openInterest"]) * mark, "vol24_usd": float(c["dayNtlVlm"])})

    with ThreadPoolExecutor(8) as ex:
        series = dict(zip([a["coin"] for a in assets], ex.map(lambda a: daily(a["coin"]), assets)))

    btc = series["BTC"]
    btc_close = {t: c for t, _, _, c, _ in btc}
    def btc_ret(n):
        return pct(btc[-1][3], btc[-1 - n][3])

    oi_hist = oi_history(today)
    out = []
    for a in assets:
        s = series.get(a["coin"]) or []
        if len(s) < 8:
            continue
        closes = [x[3] for x in s]
        vols = [x[4] for x in s]
        last = closes[-1]
        r7 = pct(last, closes[-8])
        r30 = pct(last, closes[-31]) if len(s) > 31 else None
        v7 = sum(vols[-7:]) / 7
        v30 = sum(vols[-30:]) / min(30, len(vols))
        ath = max(x[1] for x in s)
        h30 = max(x[1] for x in s[-30:])
        l30 = min(x[2] for x in s[-30:])
        past = oi_hist.get(a["coin"], [])
        oi_avg = sum(v for _, v in past[-30:]) / len(past[-30:]) if past else None
        out.append({
            "coin": a["coin"], "prix": round(a["mark"], 6),
            "age_jours": len(s), "nouveau_60j": len(s) <= 60,
            "perf_7j": round(r7, 1), "perf_30j": None if r30 is None else round(r30, 1),
            "rel_btc_7j": round(r7 - btc_ret(7), 1),
            "rel_btc_30j": None if r30 is None else round(r30 - btc_ret(30), 1),
            "vol_7j_vs_30j": round(v7 / v30, 2) if v30 else None,
            "vol24_musd": round(a["vol24_usd"] / 1e6, 2), "oi_musd": round(a["oi_usd"] / 1e6, 2),
            "oi_vs_moy": round(a["oi_usd"] / oi_avg, 2) if oi_avg else None,
            "oi_jours_historique": len(past),
            "funding_an_pct": round(a["funding_an"], 1),
            "dist_ath_pct": round(pct(a["mark"], ath), 1), "dist_haut30_pct": round(pct(a["mark"], h30), 1),
            "pos_range30": round((a["mark"] - l30) / (h30 - l30), 2) if h30 > l30 else None,
        })

    folder = os.path.join(ROOT, "donnees")
    with open(os.path.join(folder, f"oi-{today}.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["coin", "oi_usd", "prix"])
        for a in assets:
            w.writerow([a["coin"], round(a["oi_usd"]), a["mark"]])
    with open(os.path.join(folder, f"scan-{today}.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    print(f"{len(out)} actifs scannés ; BTC 7j {btc_ret(7):+.1f}%, 30j {btc_ret(30):+.1f}%")


if __name__ == "__main__":
    main()
