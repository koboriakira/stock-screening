# 新しいデータプロバイダの追加

## 概要

新しい外部データソース（API やスクレイピング）を接続してチェック項目を実データ化する手順。

## 現在の継承チェーン

```
StubEvaluationDataProvider           # ベース: 全 NEEDS_REVIEW / None
  └─ YFinanceEvaluationDataProvider  # yfinance: earningsGrowth, PER percentile
       └─ EdinetEvaluationDataProvider  # EDINET: 不正会計, 継続企業
```

## 手順

### 1. API クライアントを作成

`src/stock_screener/evaluation/infrastructure/{name}_client.py` に API クライアントを作成。

テストは `tests/evaluation/test_{name}_client.py` に。API 呼び出しはすべてモックする。

```python
class NewClient:
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def fetch_data(self, ticker: str) -> dict:
        # API 呼び出し
        ...
```

### 2. プロバイダクラスを作成

`src/stock_screener/evaluation/infrastructure/{name}_eval_provider.py`

現在の最下位プロバイダ（`EdinetEvaluationDataProvider`）を継承し、該当メソッドをオーバーライドする。

```python
class NewEvaluationDataProvider(EdinetEvaluationDataProvider):
    def __init__(self, new_client: NewClient | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._new_client = new_client

    def some_check_method(self, ticker: Ticker) -> CheckStatus:
        if self._new_client is None:
            return super().some_check_method(ticker)
        # 実データによるチェック
        ...
```

**重要**: クライアントが `None` の場合は `super()` にフォールバックすること。

### 3. CLI のプロバイダ構築を更新

`src/stock_screener/cli.py` の `_build_eval_provider()` を更新。

環境変数の有無でプロバイダを切り替えるパターン:

```python
def _build_eval_provider():
    edinet_client = ...
    new_client = None
    api_key = os.environ.get("NEW_API_KEY")
    if api_key:
        new_client = NewClient(api_key=api_key)
    return NewEvaluationDataProvider(new_client=new_client, edinet_client=edinet_client)
```

### 4. テストを書く

- クライアントテスト: API 呼び出しを `unittest.mock.patch` でモック
- プロバイダテスト: クライアントを `MagicMock` でモック
- CLI テスト: `_build_eval_provider` を `patch` でモック

### 5. 環境変数を CLAUDE.md に追記

新しい環境変数を `CLAUDE.md` の環境変数セクションに追記する。
