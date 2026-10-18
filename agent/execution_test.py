"""Test d'exécution réelle, aller-retour : vérifie toute la chaîne sans parier sur le marché.

1. ouvre la plus petite position possible (≈ 11 $ de BTC, minimum Hyperliquid 10 $), marge isolée 3x ;
2. pose le stop (−3 %) et l'objectif (+3 %) comme dans un vrai trade ;
3. vérifie sur l'exchange que la position et les deux ordres existent ;
4. ferme la position et annule les ordres restants, puis vérifie que tout est propre.

Coût attendu : quelques centimes (frais et écart achat/vente). L'état de l'agent n'est pas modifié."""

import os
import time

from . import hyperliquid, notify
from .live import _status, floor_sz, round_px

COIN = "BTC"
NOTIONAL = 11.5


def run():
    key, address = os.environ.get("HL_API_PRIVATE_KEY"), os.environ.get("HL_ACCOUNT_ADDRESS")
    if not key or not address:
        print("HL_API_PRIVATE_KEY ou HL_ACCOUNT_ADDRESS manquante.")
        return 1
    from eth_account import Account
    from hyperliquid.exchange import Exchange
    from hyperliquid.info import Info
    from hyperliquid.utils import constants

    info = Info(constants.MAINNET_API_URL, skip_ws=True)
    ex = Exchange(Account.from_key(key), constants.MAINNET_API_URL, account_address=address)
    report = []

    def log(msg):
        print(msg)
        report.append(msg)

    def position():
        for p in info.user_state(address)["assetPositions"]:
            if p["position"]["coin"] == COIN and float(p["position"]["szi"]) != 0:
                return p["position"]
        return None

    def trigger_orders():
        return [o for o in info.frontend_open_orders(address) if o["coin"] == COIN and o.get("isTrigger")]

    if position():
        log(f"Une position {COIN} existe déjà : test annulé pour ne pas y toucher.")
        return 1

    szd = hyperliquid.asset_contexts()[COIN]["sz_decimals"]
    mid = hyperliquid.mid_prices()[COIN]
    size = floor_sz(NOTIONAL / mid, szd)
    log(f"1. Ouverture test : achat {size} {COIN} (≈ {size * mid:.2f} $), marge isolée 3x")
    lev = ex.update_leverage(3, COIN, is_cross=False)
    log(f"   Levier : {lev.get('status') if isinstance(lev, dict) else lev}")
    kind, detail = _status(ex.market_open(COIN, True, size, slippage=0.01))
    if kind != "filled":
        log(f"   ✗ Ordre refusé : {detail}")
        notify.send("Test d'exécution : ÉCHEC", "\n".join(report), priority=5, tags=["rotating_light"])
        return 1
    fill, size = float(detail["avgPx"]), float(detail["totalSz"])
    log(f"   ✓ Exécuté : {size} @ {fill}")

    ok = True
    try:
        for label, tpsl, px in (("Stop", "sl", fill * 0.97), ("Objectif", "tp", fill * 1.03)):
            limit = round_px(px * 0.95, szd)
            k, d = _status(ex.order(COIN, False, size, limit,
                                    {"trigger": {"triggerPx": round_px(px, szd), "isMarket": True, "tpsl": tpsl}},
                                    reduce_only=True))
            log(f"2. {label} à {round_px(px, szd)} : {'✓ posé' if k != 'error' else '✗ ' + str(d)}")
            ok &= k != "error"
        time.sleep(2)
        pos, orders = position(), trigger_orders()
        log(f"3. Vérification : position {'✓ présente' if pos else '✗ absente'}, "
            f"{len(orders)} ordre(s) stop/objectif sur l'exchange")
        ok &= bool(pos) and len(orders) == 2
    finally:
        k, d = _status(ex.market_close(COIN, slippage=0.01))
        log(f"4. Fermeture : {'✓ ' + str(d.get('avgPx')) if k == 'filled' else '✗ ' + str(d)}")
        time.sleep(2)
        for o in trigger_orders():
            ex.cancel(COIN, o["oid"])
        time.sleep(1)
        clean = position() is None and not trigger_orders()
        log(f"   Compte propre après le test : {'✓' if clean else '✗ VÉRIFIEZ SUR HYPERLIQUID'}")
        ok &= clean and k == "filled"

    log("RÉSULTAT : " + ("✅ toute la chaîne fonctionne" if ok else "❌ un problème a été détecté"))
    notify.send("Test d'exécution : " + ("réussi ✅" if ok else "ÉCHEC ❌"), "\n".join(report),
                priority=4 if ok else 5, tags=["white_check_mark" if ok else "rotating_light"])
    return 0 if ok else 1
