from __future__ import annotations

import logging

import pandas as pd
import requests
import yfinance as yf

from stock_screener.evaluation.domain.check import CheckStatus
from stock_screener.evaluation.infrastructure.stub_provider import StubEvaluationDataProvider
from stock_screener.shared.types import Ticker

GOING_CONCERN_EQUITY_RATIO_MIN = 0.10

logger = logging.getLogger(__name__)


def compute_per_percentile(
    monthly_prices: pd.DataFrame,
    eps_series: pd.Series,
    current_per: float,
) -> float | None:
    """現在の PER が過去の PER 分布の何パーセンタイルに位置するかを算出する。

    月次終値と年次 EPS から各月の PER を算出し、現在の PER 以下の割合を返す。
    データが不足(6ポイント未満)の場合は None を返す。

    Args:
        monthly_prices: 月次株価データ(Close カラムを含む DataFrame)。
        eps_series: 年次 Diluted EPS の Series。
        current_per: 現在の PER 値。

    Returns:
        パーセンタイル値(0.0-100.0)、またはデータ不足時に None。
    """
    if monthly_prices.empty or eps_series.empty:
        return None

    eps_sorted = eps_series.sort_index()
    positive_eps = eps_sorted[eps_sorted > 0]
    if positive_eps.empty:
        return None

    # タイムゾーン統一: 両方tz-naiveにする
    if hasattr(monthly_prices.index, "tz") and monthly_prices.index.tz is not None:
        monthly_prices = monthly_prices.copy()
        monthly_prices.index = monthly_prices.index.tz_localize(None)
    if hasattr(positive_eps.index, "tz") and positive_eps.index.tz is not None:
        positive_eps = positive_eps.copy()
        positive_eps.index = positive_eps.index.tz_localize(None)

    historical_pers: list[float] = []
    for date, row in monthly_prices.iterrows():
        price = row["Close"]
        if price is None or price <= 0:
            continue
        applicable_eps = positive_eps[positive_eps.index <= date]
        if applicable_eps.empty:
            continue
        eps = applicable_eps.iloc[-1]
        per = price / eps
        if per > 0:
            historical_pers.append(per)

    if len(historical_pers) < 6:
        return None

    count_below = sum(1 for p in historical_pers if p <= current_per)
    return 100.0 * count_below / len(historical_pers)


class YFinanceEvaluationDataProvider(StubEvaluationDataProvider):
    """yfinance API を利用した評価データプロバイダ。

    StubEvaluationDataProvider を継承し、Gate2 の利益成長予想(2A-2)と
    Gate3 の PER パーセンタイル(3-2)を yfinance の実データで実装する。
    """

    def check_going_concern(self, ticker: Ticker) -> CheckStatus:
        """yfinance のバランスシートから自己資本比率を算出し、GC リスクを簡易判定する。

        自己資本比率 < 10% の場合は FAIL を返す。
        データ取得できない場合や 10% 以上の場合は NEEDS_REVIEW(EDINET 未接続のため)。
        """
        try:
            yf_ticker = yf.Ticker(ticker.symbol)
            bs = yf_ticker.balance_sheet
            if bs is None or bs.empty:
                return CheckStatus.NEEDS_REVIEW
            if "Stockholders Equity" not in bs.index or "Total Assets" not in bs.index:
                return CheckStatus.NEEDS_REVIEW

            # 最新期のデータを使用
            equity = bs.loc["Stockholders Equity"].iloc[0]
            assets = bs.loc["Total Assets"].iloc[0]
            if assets is None or assets <= 0:
                return CheckStatus.NEEDS_REVIEW

            equity_ratio = float(equity) / float(assets)
            if equity_ratio < GOING_CONCERN_EQUITY_RATIO_MIN:
                return CheckStatus.FAIL
        except (requests.exceptions.RequestException, KeyError, ValueError, TypeError, IndexError):
            logger.warning("Failed to check going concern for %s", ticker.symbol)

        return CheckStatus.NEEDS_REVIEW

    def get_earnings_growth_forecast(self, ticker: Ticker) -> float | None:
        """yfinance から予想利益成長率(earningsGrowth)を取得する。"""
        try:
            info = yf.Ticker(ticker.symbol).info
        except (requests.exceptions.RequestException, KeyError, ValueError, TypeError):
            logger.warning("Failed to fetch earningsGrowth for %s", ticker.symbol)
            return None
        value = info.get("earningsGrowth")
        if value is None:
            return None
        return float(value)

    def get_per_percentile_in_5y_range(self, ticker: Ticker) -> float | None:
        """過去5年間の月次データから現在の PER パーセンタイルを算出する。"""
        try:
            yf_ticker = yf.Ticker(ticker.symbol)
            info = yf_ticker.info
            current_per = info.get("trailingPE") or info.get("forwardPE")
            if current_per is None:
                return None

            history = yf_ticker.history(period="5y", interval="1mo")
            if history.empty:
                return None

            financials = yf_ticker.financials
            if financials is None or financials.empty:
                return None
            if "Diluted EPS" not in financials.index:
                return None

            eps_series = financials.loc["Diluted EPS"].dropna()
            return compute_per_percentile(history, eps_series, float(current_per))
        except (requests.exceptions.RequestException, KeyError, ValueError, TypeError):
            logger.warning("Failed to fetch PER percentile for %s", ticker.symbol)
            return None
