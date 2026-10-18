"""Client minimal pour l'endpoint public /info de Hyperliquid (lecture seule, aucune clé)."""

import json
import time
import urllib.request

API_URL = "https://api.hyperliquid.xyz/info"

INTERVAL_MS = {
    "1m": 60_000, "5m": 300_000, "15m": 900_000, "1h": 3_600_000,
    "4h": 14_400_000, "1d": 86_400_000,
}


def _post(payload, retries=3):
    data = json.dumps(payload).encode()
    for attempt in range(retries):
        try:
            req = urllib.request.Request(API_URL, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read())
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)


def mid_prices():
    return {k: float(v) for k, v in _post({"type": "allMids"}).items() if not k.startswith("@") and not k.startswith("#")}


def candles(coin, interval, bars):
    """Renvoie les bougies clôturées, de la plus ancienne à la plus récente."""
    step = INTERVAL_MS[interval]
    end = int(time.time() * 1000)
    out = []
    # L'API renvoie au plus 5000 bougies par requête.
    while len(out) < bars:
        n = min(5000, bars - len(out))
        start = end - n * step
        chunk = _post({"type": "candleSnapshot",
                       "req": {"coin": coin, "interval": interval, "startTime": start, "endTime": end}})
        if not chunk:
            break
        out = [_parse(c) for c in chunk] + out
        end = start
    out.sort(key=lambda c: c["t"])
    dedup = {c["t"]: c for c in out}
    now = int(time.time() * 1000)
    return [c for c in dedup.values() if c["close_time"] < now][-bars:]


def _parse(c):
    return {"t": c["t"], "close_time": c["T"], "open": float(c["o"]), "high": float(c["h"]),
            "low": float(c["l"]), "close": float(c["c"]), "volume": float(c["v"])}


def asset_contexts():
    """Funding horaire, open interest et prix mark par actif."""
    meta, ctxs = _post({"type": "metaAndAssetCtxs"})
    out = {}
    for asset, ctx in zip(meta["universe"], ctxs):
        out[asset["name"]] = {
            "funding": float(ctx["funding"]),
            "open_interest": float(ctx["openInterest"]),
            "mark": float(ctx["markPx"]),
            "max_leverage": asset["maxLeverage"],
            "sz_decimals": asset["szDecimals"],
        }
    return out
