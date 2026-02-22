from __future__ import annotations

from stock_screener.evaluation.domain.check import CheckStatus
from stock_screener.evaluation.domain.evaluation_report import Verdict
from stock_screener.evaluation.domain.evaluation_target import EvaluationTarget
from stock_screener.evaluation.infrastructure.stub_provider import StubEvaluationDataProvider
from stock_screener.evaluation.service import EvaluationService
from stock_screener.market_data.domain.financial_snapshot import FinancialSnapshot
from stock_screener.shared.types import Ticker


def _make_target(
    ticker: str = "1234",
    per: float | None = 10.0,
    pbr: float | None = 0.8,
    net_cash_ratio: float | None = 0.25,
    **kwargs,
) -> EvaluationTarget:
    defaults = {
        "ticker": Ticker(ticker),
        "company_name": "テスト株",
        "sector": "電気機器",
        "financial_snapshot": FinancialSnapshot(per=per, pbr=pbr, net_cash_ratio=net_cash_ratio),
        "discovery_rank": 1,
        "score_total": 50.0,
    }
    defaults.update(kwargs)
    return EvaluationTarget(**defaults)


class EarningsGrowthProvider(StubEvaluationDataProvider):
    def __init__(self, growth: float):
        self._growth = growth

    def get_earnings_growth_forecast(self, ticker: Ticker) -> float | None:
        return self._growth


class FraudProvider(StubEvaluationDataProvider):
    def check_accounting_fraud(self, ticker: Ticker) -> CheckStatus:
        return CheckStatus.FAIL


class TestEvaluationService:
    def test_invest_verdict(self):
        target = _make_target(pbr=0.7, net_cash_ratio=0.35)
        provider = EarningsGrowthProvider(0.30)
        service = EvaluationService(provider)
        reports = service.execute([target])
        assert len(reports) == 1
        assert reports[0].verdict == Verdict.INVEST

    def test_reject_gate1_fail(self):
        target = _make_target()
        provider = FraudProvider()
        service = EvaluationService(provider)
        reports = service.execute([target])
        assert reports[0].verdict == Verdict.REJECT

    def test_watchlist_no_catalyst(self):
        target = _make_target()
        provider = StubEvaluationDataProvider()
        service = EvaluationService(provider)
        reports = service.execute([target])
        assert reports[0].verdict == Verdict.WATCHLIST

    def test_multiple_targets(self):
        targets = [_make_target(ticker=str(i).zfill(4)) for i in range(1000, 1003)]
        provider = StubEvaluationDataProvider()
        service = EvaluationService(provider)
        reports = service.execute(targets)
        assert len(reports) == 3

    def test_gate1_fail_skips_gate2_gate3(self):
        target = _make_target()
        provider = FraudProvider()
        service = EvaluationService(provider)
        reports = service.execute([target])
        report = reports[0]
        assert report.verdict == Verdict.REJECT
        assert report.gate1.passed is False
        assert len(report.gate2.checks) == 0
        assert len(report.gate3.checks) == 0

    def test_report_has_evaluated_at(self):
        target = _make_target()
        provider = StubEvaluationDataProvider()
        service = EvaluationService(provider)
        reports = service.execute([target])
        assert reports[0].evaluated_at is not None

    def test_anomaly_flags_skip_gate_evaluation(self):
        """異常値フラグのある銘柄はGate評価をスキップしWATCHLIST判定になる。"""
        target = _make_target(
            anomaly_flags=["[domain_range:pbr=0.002]", "[domain_range:operating_profit_growth=1553.555]"],
        )
        provider = EarningsGrowthProvider(0.30)
        service = EvaluationService(provider)
        reports = service.execute([target])
        report = reports[0]
        assert report.verdict == Verdict.WATCHLIST
        assert len(report.gate1.checks) == 0
        assert len(report.gate2.checks) == 0
        assert len(report.gate3.checks) == 0
        assert report.verdict_reason is not None
        assert "異常値" in report.verdict_reason

    def test_no_anomaly_flags_normal_evaluation(self):
        """異常値フラグがない銘柄は通常のGate評価が実行される。"""
        target = _make_target(anomaly_flags=[])
        provider = StubEvaluationDataProvider()
        service = EvaluationService(provider)
        reports = service.execute([target])
        report = reports[0]
        assert len(report.gate1.checks) > 0
        assert report.verdict_reason is None
