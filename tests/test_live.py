import os
import tempfile
import unittest
from unittest import mock

from agent import live
from agent.analyst import Verdict
from agent.strategies import Signal

COINS_META = {c: {"funding": 0.0, "open_interest": 1.0, "mark": 1.0, "max_leverage": 40, "sz_decimals": d}
              for c, d in (("BTC", 5), ("ETH", 4), ("SOL", 2))}
MIDS = {"BTC": 82000.0, "ETH": 2400.0, "SOL": 100.0}


def candles(n=300):
    return [{"t": i * 86_400_000, "close_time": i * 86_400_000 + 1, "open": 100.0, "high": 101.0,
             "low": 99.0, "close": 100.0, "volume": 1.0} for i in range(n)]


class FakeInfo:
    def __init__(self, equity=27.0, positions=None, orders=None):
        self.equity, self.positions, self.orders = equity, positions or [], orders or []

    def user_state(self, addr):
        return {"marginSummary": {"accountValue": str(self.equity)},
                "assetPositions": [{"position": p} for p in self.positions]}

    def frontend_open_orders(self, addr):
        return self.orders


class FakeExchange:
    def __init__(self, reject_stop=False):
        self.calls, self.reject_stop = [], reject_stop

    def update_leverage(self, *a, **k):
        self.calls.append(("leverage", a, k))

    def market_open(self, coin, is_buy, sz, slippage):
        self.calls.append(("open", coin, is_buy, sz))
        return {"status": "ok", "response": {"data": {"statuses": [
            {"filled": {"totalSz": str(sz), "avgPx": str(MIDS[coin]), "oid": 1}}]}}}

    def order(self, coin, is_buy, sz, limit, order_type, reduce_only):
        tpsl = order_type["trigger"]["tpsl"]
        self.calls.append((tpsl, coin, is_buy, sz, order_type["trigger"]["triggerPx"], reduce_only))
        if tpsl == "sl" and self.reject_stop:
            return {"status": "ok", "response": {"data": {"statuses": [{"error": "refusé"}]}}}
        return {"status": "ok", "response": {"data": {"statuses": [{"resting": {"oid": 2}}]}}}

    def market_close(self, coin):
        self.calls.append(("close", coin))

    def cancel(self, coin, oid):
        self.calls.append(("cancel", coin, oid))


class PlanEntryTests(unittest.TestCase):
    def sig(self, stop):
        return Signal("BTC", "long", 82000.0, stop, 92000.0, "donchian", "test")

    def test_two_dollar_risk_on_small_account(self):
        size, why = live.plan_entry(self.sig(77000.0), 82000.0, 27.0, 2.0, live.LiveConfig(), 5)
        self.assertIsNone(why)
        self.assertAlmostEqual(size, 0.0004)
        self.assertLessEqual(size * 5000, 2.0)

    def test_below_exchange_minimum_is_skipped(self):
        size, why = live.plan_entry(self.sig(77000.0), 82000.0, 27.0, 0.27, live.LiveConfig(), 5)
        self.assertEqual(size, 0.0)
        self.assertIn("minimum", why)

    def test_leverage_cap(self):
        size, _ = live.plan_entry(self.sig(81900.0), 82000.0, 27.0, 2.0, live.LiveConfig(), 5)
        self.assertLessEqual(size * 82000, 27.0 * 3 + 1e-9)

    def test_price_rounding(self):
        self.assertEqual(live.round_px(81234.567, 5), 81235.0)
        self.assertEqual(live.round_px(2.345678, 2), 2.3457)


class CycleTests(unittest.TestCase):
    def setUp(self):
        d = tempfile.mkdtemp()
        self.lcfg = live.LiveConfig(state_path=f"{d}/s.json", log_path=f"{d}/c.log",
                                    journal_path=f"{d}/j.jsonl", stop_file=f"{d}/STOP")
        self.patches = [
            mock.patch.object(live.hyperliquid, "candles", return_value=candles()),
            mock.patch.object(live.hyperliquid, "asset_contexts", return_value=COINS_META),
            mock.patch.object(live.hyperliquid, "mid_prices", return_value=MIDS),
            mock.patch.object(live.analyst, "review", return_value=Verdict(True, "ok", [], [])),
            mock.patch.object(live.notify, "send", return_value=False),
            mock.patch.object(live.hyperliquid, "user_abstraction", return_value="default"),
        ]
        for p in self.patches:
            p.start()
        self.addCleanup(lambda: [p.stop() for p in self.patches])

    def run_cycle(self, info, ex, signal_coin="BTC"):
        def best(coin, *a, **k):
            if coin != signal_coin:
                return None
            return Signal(coin, "long", MIDS[coin], MIDS[coin] * 0.94, MIDS[coin] * 1.12, "donchian", "test")
        with mock.patch.object(live.strategies, "best_signal", side_effect=best):
            t = live.LiveTrader(ex, info, "0xabc", self.lcfg, send=True, log=lambda m: None)
            t.cycle()
        return t

    def test_opens_with_stop_and_target(self):
        ex = FakeExchange()
        t = self.run_cycle(FakeInfo(), ex)
        kinds = [c[0] for c in ex.calls]
        self.assertEqual(kinds, ["leverage", "open", "sl", "tp"])
        sl = ex.calls[2]
        self.assertFalse(sl[2])          # le stop d'un long est une vente
        self.assertTrue(sl[5])           # reduce-only
        self.assertIn("BTC", t.state["positions"])

    def test_refused_stop_closes_position(self):
        ex = FakeExchange(reject_stop=True)
        t = self.run_cycle(FakeInfo(), ex)
        self.assertIn(("close", "BTC"), ex.calls)
        self.assertNotIn("BTC", t.state["positions"])

    def test_no_new_trade_after_halt(self):
        self.run_cycle(FakeInfo(equity=27.0), FakeExchange(), signal_coin=None)  # fixe le capital de départ
        ex = FakeExchange()
        t = live.LiveTrader(ex, FakeInfo(equity=20.0), "0xabc", self.lcfg, send=True, log=lambda m: None)
        t.state["last_bar"] = {}
        with mock.patch.object(live.strategies, "best_signal",
                               return_value=Signal("BTC", "long", 82000, 77000, 92000, "donchian", "t")):
            t.cycle()
        self.assertEqual(ex.calls, [])

    def test_stop_file_blocks_entries(self):
        open(self.lcfg.stop_file, "w").close()
        ex = FakeExchange()
        self.run_cycle(FakeInfo(), ex)
        self.assertEqual(ex.calls, [])

    def test_missing_stop_is_replaced(self):
        pos = {"coin": "BTC", "szi": "0.0004", "entryPx": "82000"}
        ex = FakeExchange()
        self.run_cycle(FakeInfo(positions=[pos]), ex, signal_coin=None)
        self.assertEqual([c[0] for c in ex.calls], ["sl"])

    def test_simulation_sends_nothing(self):
        ex = FakeExchange()
        with mock.patch.object(live.strategies, "best_signal",
                               return_value=Signal("BTC", "long", 82000, 77000, 92000, "donchian", "t")):
            live.LiveTrader(ex, FakeInfo(), "0xabc", self.lcfg, send=False, log=lambda m: None).cycle()
        self.assertEqual(ex.calls, [])


    def test_unified_account_uses_spot_usdc(self):
        info = FakeInfo(equity=0.0)
        info.spot_user_state = lambda addr: {"balances": [{"coin": "USDC", "total": "25.70", "hold": "0"}]}
        ex = FakeExchange()
        with mock.patch.object(live.hyperliquid, "user_abstraction", return_value="unifiedAccount"):
            t = self.run_cycle(info, ex)
        self.assertEqual(t.state["start_equity"], 25.70)
        self.assertIn("open", [c[0] for c in ex.calls])


if __name__ == "__main__":
    unittest.main()
