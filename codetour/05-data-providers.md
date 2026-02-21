# CodeTour: データプロバイダの継承チェーンと段階的実データ化

## 設計の背景

3-Gate 評価パイプラインでは、各チェック項目ごとに異なる外部データソースが必要です。
しかし全データソースを一度に接続するのは非現実的なため、
**段階的に実データを追加** できる設計になっています。

---

## Protocol (インターフェース)

全 Gate が依存するのは `EvaluationDataProvider` Protocol のみです。

```python
# evaluation/domain/data_provider.py
class EvaluationDataProvider(Protocol):
    def check_accounting_fraud(self, ticker: Ticker) -> CheckStatus: ...
    def check_going_concern(self, ticker: Ticker) -> CheckStatus: ...
    def get_margin_trading_ratio(self, ticker: Ticker) -> float | None: ...
    def get_earnings_growth_forecast(self, ticker: Ticker) -> float | None: ...
    def get_quarterly_progress_improvement(self, ticker: Ticker) -> float | None: ...
    def has_upward_revision(self, ticker: Ticker) -> bool | None: ...
    def has_share_buyback(self, ticker: Ticker) -> bool | None: ...
    def get_per_percentile_in_5y_range(self, ticker: Ticker) -> float | None: ...
```

Gate1/2/3 はこの Protocol に依存し、具体的な実装クラスを知りません。
Python の構造的部分型 (Structural Subtyping) により、
Protocol を明示的に `class Foo(EvaluationDataProvider)` と継承する必要はなく、
同じメソッドシグネチャを持つクラスであれば自動的に準拠します。

---

## 継承チェーン

```
EvaluationDataProvider (Protocol)
    ↑ 構造的に準拠
StubEvaluationDataProvider
    ↑ 継承
YFinanceEvaluationDataProvider
    ↑ 継承
EdinetEvaluationDataProvider
```

### レイヤー 1: StubEvaluationDataProvider

全メソッドが `NEEDS_REVIEW` or `None` を返すスタブ。

```python
# evaluation/infrastructure/stub_provider.py
class StubEvaluationDataProvider:
    def check_accounting_fraud(self, ticker: Ticker) -> CheckStatus:
        return CheckStatus.NEEDS_REVIEW

    def get_earnings_growth_forecast(self, ticker: Ticker) -> float | None:
        return None
    # ... 全8メソッドが安全なデフォルト値を返す
```

**用途**: 外部データソースが一切不要。テスト時やオフライン時のフォールバック。

### レイヤー 2: YFinanceEvaluationDataProvider

Stub を継承し、yfinance で取得可能な2項目をオーバーライド。

```python
# evaluation/infrastructure/yfinance_eval_provider.py
class YFinanceEvaluationDataProvider(StubEvaluationDataProvider):
    # オーバーライド: Gate2 の 2A-2
    def get_earnings_growth_forecast(self, ticker: Ticker) -> float | None:
        info = yf.Ticker(ticker.symbol).info
        return info.get("earningsGrowth")

    # オーバーライド: Gate3 の 3-2
    def get_per_percentile_in_5y_range(self, ticker: Ticker) -> float | None:
        # 過去5年の月次データから PER パーセンタイルを算出
        ...
```

**実データ化された項目**:
| チェック | メソッド | データソース |
|---|---|---|
| 2A-2 | `get_earnings_growth_forecast()` | `yfinance.Ticker.info["earningsGrowth"]` |
| 3-2 | `get_per_percentile_in_5y_range()` | `yfinance.Ticker.history()` + `financials` |

残りの6メソッドは親の Stub をそのまま継承 (NEEDS_REVIEW / None)。

### レイヤー 3: EdinetEvaluationDataProvider

YFinance を継承し、EDINET API で取得可能な2項目をオーバーライド。

```python
# evaluation/infrastructure/edinet_eval_provider.py
class EdinetEvaluationDataProvider(YFinanceEvaluationDataProvider):
    def __init__(self, edinet_client: EdinetClient | None = None):
        self._edinet_client = edinet_client

    # オーバーライド: Gate1 の 1-1
    def check_accounting_fraud(self, ticker: Ticker) -> CheckStatus:
        if self._edinet_client is None:
            return CheckStatus.NEEDS_REVIEW  # フォールバック
        sec_code = self._edinet_client.ticker_to_sec_code(ticker.symbol)
        filings = self._edinet_client.find_filings_by_sec_code(
            sec_code, doc_type_codes=["130"], days=1095,  # 3年
        )
        return CheckStatus.NEEDS_REVIEW if filings else CheckStatus.PASS

    # オーバーライド: Gate1 の 1-2
    def check_going_concern(self, ticker: Ticker) -> CheckStatus:
        # 現状は書類存在確認のみ → 常に NEEDS_REVIEW
        ...
```

**実データ化された項目**:
| チェック | メソッド | データソース |
|---|---|---|
| 1-1 | `check_accounting_fraud()` | EDINET 訂正報告書 (docTypeCode=130) |
| 1-2 | `check_going_concern()` | EDINET 有価証券報告書 (docTypeCode=120) |

---

## 各チェック項目の実装状況

| ID | 項目 | Provider | 状態 |
|---|---|---|---|
| 1-1 | 不正会計 | Edinet | 訂正報告書の有無で判定 |
| 1-2 | GC 注記 | Edinet | 書類存在確認のみ (XBRL 解析は未実装) |
| 1-5 | 信用倍率 | Stub | データソース未接続 |
| 2A-1 | 四半期進捗率 | Stub | データソース未接続 |
| 2A-2 | 利益成長予想 | YFinance | `earningsGrowth` から取得 |
| 2A-3 | 上方修正 | Stub | データソース未接続 |
| 2B-2 | 自社株買い | Stub | データソース未接続 |
| 2D-2 | TOB/MBO 構造 | (データ不要) | FinancialSnapshot から判定 |
| 3-2 | PER パーセンタイル | YFinance | 5年月次データから算出 |
| 3-3 | ネットキャッシュ | (データ不要) | FinancialSnapshot から判定 |

---

## CLI での Provider 選択

```python
# cli.py
def _build_eval_provider() -> YFinanceEvaluationDataProvider:
    edinet_api_key = os.environ.get("EDINET_API_KEY")
    if edinet_api_key:
        client = EdinetClient(api_key=edinet_api_key)
        return EdinetEvaluationDataProvider(edinet_client=client)
    return YFinanceEvaluationDataProvider()
```

- `EDINET_API_KEY` 環境変数が設定 → `EdinetEvaluationDataProvider` (yfinance + EDINET)
- 未設定 → `YFinanceEvaluationDataProvider` (yfinance のみ)

---

## 新しいデータソースの追加方法

1. `YFinanceEvaluationDataProvider` (or `EdinetEvaluationDataProvider`) を継承
2. 対象のメソッドをオーバーライド
3. CLI の `_build_eval_provider()` に新しい条件分岐を追加

例: TDnet API で自社株買いデータを取得する場合

```python
class TdnetEvaluationDataProvider(EdinetEvaluationDataProvider):
    def has_share_buyback(self, ticker: Ticker) -> bool | None:
        # TDnet API から自社株買い情報を取得
        ...
```

継承チェーンの末端に追加するだけで、他のチェック項目は既存の実装がそのまま動きます。
