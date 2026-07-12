from __future__ import annotations

import json
import math
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

_JST = ZoneInfo("Asia/Tokyo")

# exit code 2 (入力エラー) 系
INVALID_TICKER = "invalid_ticker"
INVALID_ARGUMENT = "invalid_argument"

# exit code 1 (データソースエラー) 系
RATE_LIMITED = "rate_limited"
NETWORK_ERROR = "network_error"
NO_DATA = "no_data"
DATA_SOURCE_ERROR = "data_source_error"


class InputError(Exception):
    """引数・入力ファイル起因のエラー。exit code 2 に対応する。"""

    def __init__(self, message: str, code: str = INVALID_ARGUMENT) -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class DataSourceError(Exception):
    """外部データソース起因のエラー。exit code 1 に対応する。"""

    def __init__(self, message: str, code: str = DATA_SOURCE_ERROR) -> None:
        super().__init__(message)
        self.message = message
        self.code = code


def _sanitize_scalar(value: Any) -> tuple[bool, Any]:
    """スカラー値をサニタイズする。(処理済みか, 値) を返す。"""
    if isinstance(value, np.floating):
        value = value.item()
    if isinstance(value, float):
        return True, (None if math.isnan(value) or math.isinf(value) else value)
    if isinstance(value, np.integer):
        return True, value.item()
    if isinstance(value, np.bool_):
        return True, bool(value)
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return True, value.isoformat()
    return False, value


def _sanitize(value: Any) -> Any:
    """pandas/numpy 由来の値を JSON シリアライズ可能な Python ネイティブ型へ再帰変換する。"""
    handled, scalar = _sanitize_scalar(value)
    if handled:
        return scalar
    if is_dataclass(value) and not isinstance(value, type):
        return _sanitize(asdict(value))
    if isinstance(value, dict):
        return {k: _sanitize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize(v) for v in value]
    return value


def render_success(
    type_: str,
    items: list[Any],
    source: str,
    *,
    errors: list[Any] | None = None,
    cache_hit: bool = False,
) -> str:
    """成功レスポンスの JSON エンベロープ文字列を生成する。

    キー順は type -> count -> items -> (errors) -> source -> fetched_at -> cache_hit で固定。
    errors は None または空リストのとき出力に含めない。
    """
    payload: dict[str, Any] = {
        "type": type_,
        "count": len(items),
        "items": _sanitize(items),
    }
    if errors:
        payload["errors"] = _sanitize(errors)
    payload["source"] = source
    payload["fetched_at"] = datetime.now(_JST).isoformat(timespec="seconds")
    payload["cache_hit"] = cache_hit
    return json.dumps(payload, ensure_ascii=False, allow_nan=False)


def render_error(code: str, message: str) -> str:
    """エラーレスポンスの JSON エンベロープ文字列を生成する。"""
    payload = {"type": "error", "error": {"code": code, "message": message}}
    return json.dumps(payload, ensure_ascii=False, allow_nan=False)
