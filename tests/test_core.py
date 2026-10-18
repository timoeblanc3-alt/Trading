import unittest

from agent import indicators as ind
from agent import risk
from agent.config import Config, RiskConfig
from agent.portfolio import Portfolio
from agent.strategies import Signal

GROUPS = [{"BTC", "ETH", "SOL"}]


def sig(coin="BTC", side="long", entry=60000.0, stop=58800.0, target=63600.0):
    return Signal(coin, side, entry, stop, target, "test", "test")


class IndicatorTests(unittest.TestCase):
    def test_sma_and_ema(self):
        self.assertEqual(ind.sma([1, 2, 3, 4], 2), [None, 1.5, 2.5, 3.5])
        e = ind.ema([1, 2, 3, 4, 5], 3)
        self.assertEqual(e[:2], [None, None])
        self.assertAlmostEqual(e[2], 2.0)
        self.assertAlmostEqual(e[3], 3.0)

    def test_rsi_extremes(self):
        self.assertEqual(ind.rsi(list(range(1, 40)), 14)[-1], 100.0)
        self.assertAlmostEqual(ind.rsi(list(range(40, 1, -1)), 14)[-1], 0.0)

    def test_donchian_excludes_current_bar(self):
        up, lo = ind.donchian([1, 2, 3, 10], [0, 1, 2, 9], 3)
        self.assertEqual(up[3], 3)
        self.assertEqual(lo[3], 0)

    def test_atr_constant_range(self):
        a = ind.atr([11] * 30, [9] * 30, [10] * 30, 14)
        self.assertAlmostEqual(a[-1], 2.0)


class RiskTests(unittest.TestCase):
    def test_one_percent_sizing(self):
        # Exemple du bilan : 10 000 $, 1 %, stop à 1 200 $ → 0,0833 BTC.
        d = risk.evaluate(sig(), RiskConfig(), 10000, 10000, 10000, [], GROUPS)
        self.assertTrue(d.approved)
        self.assertAlmostEqual(d.size, 100 / 1200)

    def test_correlated_risk_capped(self):
        open_btc = [{"coin": "BTC", "side": "long", "entry": 60000, "stop": 58800, "size": 100 / 1200}]
        d = risk.evaluate(sig("ETH", entry=3000, stop=2900, target=3300), RiskConfig(),
                          10000, 10000, 10000, open_btc, GROUPS)
        self.assertTrue(d.approved)
        self.assertAlmostEqual(d.risk_amount, 100)  # 2 % de corrélé max − 1 % déjà pris
        open_two = open_btc + [{"coin": "ETH", "side": "long", "entry": 3000, "stop": 2900, "size": 1.0}]
        d = risk.evaluate(sig("SOL", entry=100, stop=95, target=115), RiskConfig(),
                          10000, 10000, 10000, open_two, GROUPS)
        self.assertFalse(d.approved)

    def test_drawdown_halves_then_halts(self):
        cfg = RiskConfig()
        d = risk.evaluate(sig(), cfg, 8900, 10000, 8900, [], GROUPS)
        self.assertAlmostEqual(d.risk_amount, 8900 * 0.005)
        d = risk.evaluate(sig(), cfg, 8400, 10000, 8400, [], GROUPS)
        self.assertFalse(d.approved)

    def test_daily_loss_limit(self):
        d = risk.evaluate(sig(), RiskConfig(), 9690, 10000, 10000, [], GROUPS)
        self.assertFalse(d.approved)

    def test_leverage_cap(self):
        d = risk.evaluate(sig(stop=59990, target=60100), RiskConfig(), 10000, 10000, 10000, [], GROUPS)
        self.assertAlmostEqual(d.size * 60000, 30000)

    def test_low_reward_risk_rejected(self):
        d = risk.evaluate(sig(target=61000), RiskConfig(), 10000, 10000, 10000, [], GROUPS)
        self.assertFalse(d.approved)


class PortfolioTests(unittest.TestCase):
    def test_stop_loss_costs_about_one_r(self):
        cfg = Config(starting_equity=10000)
        pf = Portfolio(cfg)
        pf.try_open(sig(), 0, {"BTC": 60000})
        x = {"open": [60000], "high": [60100], "low": [58000], "close": [58500]}
        trade = pf.manage("BTC", x, 0, 1)[0]
        self.assertEqual(trade["exit_reason"], "stop")
        self.assertLess(trade["r"], -1.0)       # frais et slippage en plus
        self.assertGreater(trade["r"], -1.2)
        self.assertFalse(pf.positions)


class AnalystVetoTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        from agent import __main__ as cli
        self.cli = cli
        self.tmp = tempfile.mkdtemp()
        self.cfg = Config(starting_equity=10000, analyst_log_path=f"{self.tmp}/a.jsonl")
        self.x = {"rsi": [55.0], "adx": [30.0], "atr": [600.0], "ema200": [55000.0]}

    def _open(self, verdict):
        from unittest import mock
        from agent.analyst import Verdict
        pf = Portfolio(self.cfg)
        with mock.patch.object(self.cli.analyst, "review", return_value=Verdict(verdict, "test", [], [])):
            msg = self.cli.open_signal(self.cfg, pf, sig(), 0, {"BTC": 60000}, self.x, 0, {})
        return pf, msg

    def test_veto_blocks_trade(self):
        pf, msg = self._open(False)
        self.assertFalse(pf.positions)
        self.assertIn("REFUSÉ", msg)

    def test_approval_still_goes_through_risk_manager(self):
        pf, msg = self._open(True)
        self.assertEqual(len(pf.positions), 1)
        self.assertAlmostEqual(pf.positions[0]["size"] * pf.positions[0]["initial_risk"], 100, delta=1)

    def test_analyst_disabled_without_key(self):
        import os
        from unittest import mock
        from agent import analyst
        with mock.patch.dict(os.environ, {}, clear=True):
            v = analyst.review(sig(), {})
        self.assertTrue(v.approved)
        self.assertFalse(v.available)


if __name__ == "__main__":
    unittest.main()


class ExploreTests(unittest.TestCase):
    def test_breakout_trade_is_stopped_at_about_minus_one_r(self):
        from agent import explore as E
        n = 260
        cs = [{"t": i * E.DAY, "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0 + 0.5 * (i % 2),
               "volume": 1.0} for i in range(n)]
        cs[-3].update(close=110.0, high=110.5)          # cassure à la hausse
        cs[-2].update(open=110.0, high=110.2, low=80.0, close=81.0)  # effondrement le lendemain
        x = E.features(cs)
        v = E.Variant("test", filters=[])
        trades = E.simulate("T", x, v, {"btc": {}})
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0]["side"], "long")
        self.assertLess(trades[0]["r"], -1.0)
        self.assertGreater(trades[0]["r"], -1.3)
