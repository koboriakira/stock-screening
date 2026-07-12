from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime

import numpy as np
import pandas as pd

from stock_screener.shared.json_output import (
    DataSourceError,
    InputError,
    render_error,
    render_success,
)


class TestRenderSuccess:
    def test_key_order_without_errors(self):
        result = render_success("quote", [{"ticker": "1234.T"}], "yfinance")
        assert list(json.loads(result).keys()) == [
            "type",
            "count",
            "items",
            "source",
            "fetched_at",
            "cache_hit",
        ]

    def test_key_order_with_errors(self):
        result = render_success(
            "quote",
            [{"ticker": "1234.T"}],
            "yfinance",
            errors=[{"ticker": "9999.T", "code": "no_data", "message": "not found"}],
        )
        assert list(json.loads(result).keys()) == [
            "type",
            "count",
            "items",
            "errors",
            "source",
            "fetched_at",
            "cache_hit",
        ]

    def test_count_is_derived_from_items_length(self):
        result = render_success("quote", [{"a": 1}, {"a": 2}, {"a": 3}], "yfinance")
        assert json.loads(result)["count"] == 3

    def test_errors_omitted_when_none(self):
        result = render_success("quote", [], "yfinance", errors=None)
        assert "errors" not in json.loads(result)

    def test_errors_omitted_when_empty_list(self):
        result = render_success("quote", [], "yfinance", errors=[])
        assert "errors" not in json.loads(result)

    def test_errors_included_when_present(self):
        errors = [{"ticker": "9999.T", "code": "no_data", "message": "not found"}]
        result = render_success("quote", [], "yfinance", errors=errors)
        assert json.loads(result)["errors"] == errors

    def test_cache_hit_default_false(self):
        result = render_success("quote", [], "yfinance")
        assert json.loads(result)["cache_hit"] is False

    def test_cache_hit_true(self):
        result = render_success("quote", [], "yfinance", cache_hit=True)
        assert json.loads(result)["cache_hit"] is True

    def test_fetched_at_has_jst_offset(self):
        result = render_success("quote", [], "yfinance")
        fetched_at = json.loads(result)["fetched_at"]
        assert fetched_at.endswith("+09:00")

    def test_fetched_at_is_second_precision(self):
        result = render_success("quote", [], "yfinance")
        fetched_at = json.loads(result)["fetched_at"]
        # "2026-07-12T21:34:56+09:00" のようにマイクロ秒を含まない
        naive_part = fetched_at.split("+")[0]
        assert "." not in naive_part

    def test_japanese_not_escaped(self):
        result = render_success("quote", [{"name": "トヨタ自動車"}], "yfinance")
        assert "トヨタ自動車" in result
        assert "\\u" not in result

    def test_source_field(self):
        result = render_success("quote", [], "yfinance")
        assert json.loads(result)["source"] == "yfinance"

    def test_type_field(self):
        result = render_success("quote", [], "yfinance")
        assert json.loads(result)["type"] == "quote"


class TestRenderSuccessSanitize:
    def test_sanitizes_python_nan_to_none(self):
        result = render_success("quote", [{"per": float("nan")}], "yfinance")
        assert json.loads(result)["items"][0]["per"] is None

    def test_sanitizes_python_inf_to_none(self):
        result = render_success("quote", [{"per": float("inf")}], "yfinance")
        assert json.loads(result)["items"][0]["per"] is None

    def test_sanitizes_numpy_nan_to_none(self):
        result = render_success("quote", [{"per": np.float64("nan")}], "yfinance")
        assert json.loads(result)["items"][0]["per"] is None

    def test_sanitizes_numpy_scalars_to_native_types(self):
        items = [{"count": np.int64(5), "ratio": np.float64(1.5), "flag": np.bool_(True)}]
        result = render_success("quote", items, "yfinance")
        assert json.loads(result)["items"][0] == {"count": 5, "ratio": 1.5, "flag": True}

    def test_sanitizes_pandas_timestamp_naive(self):
        ts = pd.Timestamp("2026-07-12 12:00:00")
        result = render_success("quote", [{"updated": ts}], "yfinance")
        assert json.loads(result)["items"][0]["updated"] == ts.isoformat()

    def test_sanitizes_pandas_timestamp_tz_aware(self):
        ts = pd.Timestamp("2026-07-12 12:00:00", tz="Asia/Tokyo")
        result = render_success("quote", [{"updated": ts}], "yfinance")
        assert json.loads(result)["items"][0]["updated"] == ts.isoformat()

    def test_sanitizes_datetime(self):
        dt = datetime(2026, 7, 12, 9, 0, 0)  # noqa: DTZ001 (naive datetime のサニタイズを検証する意図的なケース)
        result = render_success("quote", [{"dt": dt}], "yfinance")
        assert json.loads(result)["items"][0]["dt"] == dt.isoformat()

    def test_sanitizes_date(self):
        d = date(2026, 7, 12)
        result = render_success("quote", [{"d": d}], "yfinance")
        assert json.loads(result)["items"][0]["d"] == d.isoformat()

    def test_sanitizes_dataclass(self):
        @dataclass
        class Quote:
            ticker: str
            price: float

        result = render_success("quote", [Quote(ticker="1234.T", price=100.5)], "yfinance")
        assert json.loads(result)["items"][0] == {"ticker": "1234.T", "price": 100.5}

    def test_sanitizes_nested_dict_and_list(self):
        items = [{"nested": {"a": float("nan"), "b": [1, 2, float("nan")]}}]
        result = render_success("quote", items, "yfinance")
        assert json.loads(result)["items"][0] == {"nested": {"a": None, "b": [1, 2, None]}}

    def test_sanitizes_errors_list_too(self):
        errors = [{"ticker": "9999.T", "code": "no_data", "message": "not found", "extra": np.int64(1)}]
        result = render_success("quote", [], "yfinance", errors=errors)
        assert json.loads(result)["errors"][0]["extra"] == 1


class TestRenderError:
    def test_shape(self):
        result = render_error("no_data", "データが見つかりません")
        assert json.loads(result) == {
            "type": "error",
            "error": {"code": "no_data", "message": "データが見つかりません"},
        }

    def test_japanese_not_escaped(self):
        result = render_error("no_data", "データが見つかりません")
        assert "\\u" not in result


class TestInputError:
    def test_default_code(self):
        err = InputError("bad input")
        assert err.code == "invalid_argument"
        assert err.message == "bad input"

    def test_custom_code(self):
        err = InputError("bad ticker", code="invalid_ticker")
        assert err.code == "invalid_ticker"

    def test_is_exception(self):
        assert isinstance(InputError("x"), Exception)


class TestDataSourceError:
    def test_default_code(self):
        err = DataSourceError("network down")
        assert err.code == "data_source_error"
        assert err.message == "network down"

    def test_custom_code(self):
        err = DataSourceError("rate limited", code="rate_limited")
        assert err.code == "rate_limited"

    def test_is_exception(self):
        assert isinstance(DataSourceError("x"), Exception)
