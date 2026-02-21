# CodeTour: 外部 API 連携・キャッシュ・リトライ機構

## 外部データソース一覧

| データソース | 用途 | 認証 | ライブラリ |
|---|---|---|---|
| JPX Excel | 銘柄リスト (〜4,000銘柄) | 不要 | pandas (`read_excel`) |
| yfinance | 財務データ・株価・EPS | 不要 (Yahoo Finance 無料枠) | yfinance |
| EDINET API v2 | 有価証券報告書・訂正報告書 | API キー (環境変数) | requests |

---

## yfinance アダプタ

### YFinanceSecurityRepository

スクリーニング用の財務データ取得を担当。

```python
# market_data/infrastructure/yfinance_adapter.py
class YFinanceSecurityRepository:
    def __init__(self, cache: FileCache | None = None):
        self._cache = cache

    def get_financial_snapshot(self, ticker: Ticker) -> FinancialSnapshot:
        # 1. キャッシュ確認
        # 2. キャッシュミス → yfinance から取得
        # 3. 結果をキャッシュに保存
        # 4. FinancialSnapshot を返す
```

yfinance からのデータ取得は以下の API を使用:

| API | 取得データ |
|---|---|
| `yf.Ticker(symbol).info` | PER, PBR, ROE, 時価総額, 株価 等 |
| `yf.Ticker(symbol).balance_sheet` | 総資産, 自己資本 等 |
| `yf.Ticker(symbol).financials` | 営業利益 (成長率算出用) |

### YFinanceEvaluationDataProvider

評価用の追加データ取得を担当。

| API | 取得データ | 用途 |
|---|---|---|
| `yf.Ticker(symbol).info["earningsGrowth"]` | 利益成長予想 | Gate2 (2A-2) |
| `yf.Ticker(symbol).history(period="5y", interval="1mo")` | 5年月次株価 | Gate3 (3-2) |
| `yf.Ticker(symbol).financials["Diluted EPS"]` | 年次 EPS | Gate3 (3-2) |

---

## EDINET API クライアント

### EdinetClient

```python
# evaluation/infrastructure/edinet_client.py
EDINET_API_BASE = "https://disclosure.edinet-fsa.go.jp/api/v2"

class EdinetClient:
    def __init__(self, api_key: str):
        self._api_key = api_key

    def get_documents(self, date: str) -> list[dict]:
        """指定日の提出書類一覧を取得"""
        # GET /api/v2/documents.json?date=YYYY-MM-DD&type=2&Subscription-Key=...

    def find_filings_by_sec_code(self, sec_code, doc_type_codes, days) -> list[dict]:
        """証券コードと書類種別で過去N日間の書類を検索"""
        # 日ごとに get_documents() を呼び出し、条件に合致する書類を抽出
```

### ティッカー変換

EDINET の証券コードは5桁 (末尾に0を付加):
```
Ticker("7203") → symbol = "7203.T" → sec_code = "72030"
```

```python
@staticmethod
def ticker_to_sec_code(ticker_raw: str) -> str:
    code = ticker_raw.removesuffix(".T")
    if len(code) == 4:
        return code + "0"
    return code
```

---

## ファイルキャッシュ

### FileCache

yfinance の財務データ取得を高速化するための JSON ファイルキャッシュ。

```python
# market_data/infrastructure/cache.py
class FileCache:
    def __init__(self, cache_dir=None, ttl_hours=24):
        self._cache_dir = cache_dir or Path.home() / ".cache" / "stock-screener"
        self._ttl_seconds = ttl_hours * 3600
```

**キャッシュ構造**:
```
~/.cache/stock-screener/
├── snapshot_7203.T.json
├── snapshot_8306.T.json
└── ...
```

各ファイルの内容:
```json
{
    "timestamp": 1708012345.678,
    "value": {
        "market_cap": 35000000000,
        "per": 12.5,
        "pbr": 0.8,
        ...
    }
}
```

**TTL (Time To Live)**: デフォルト24時間。
```python
def get(self, key: str) -> object | None:
    data = json.loads(path.read_text())
    if time.time() - data["timestamp"] > self._ttl_seconds:
        path.unlink()     # 期限切れ → ファイル削除
        return None
    return data["value"]  # 有効 → 値を返す
```

**キャッシュキー**: `snapshot_{ticker.symbol}` (例: `snapshot_7203.T`)

**無効化**: CLI の `--no-cache` オプションで `cache=None` を渡し、キャッシュを完全にバイパス。

---

## リトライ機構

### retry_on_rate_limit

yfinance と EDINET API の両方で使用される指数バックオフリトライ。

```python
# shared/retry.py
def retry_on_rate_limit[T](
    func: Callable[[], T],
    *,
    max_retries: int = 3,
    base_delay: float = 1.0,
    default: Any = _SENTINEL,
) -> T:
```

**対応するエラー**:
- `HTTPError` (ステータスコード 429 — レートリミット)
- `ConnectionError` (ネットワーク切断)

**バックオフ戦略**: 指数バックオフ
```
attempt 0: 即実行
attempt 1: 1.0秒待機
attempt 2: 2.0秒待機
attempt 3: 4.0秒待機 (max_retries=3 の場合)
```

**default パラメータ**: 全リトライ失敗後に例外を投げる代わりにデフォルト値を返す。
```python
# 使用例: 失敗しても空リストを返す
result = retry_on_rate_limit(_request, max_retries=2, default=[])
```

**PEP 695 型パラメータ構文**: `def retry_on_rate_limit[T](...)` は Python 3.12+ の新構文で、
ジェネリック型パラメータ `T` を簡潔に宣言しています。

---

## エラーハンドリングの方針

### 「データなし = None」の原則

外部 API 呼び出しの失敗は例外を伝播させず、`None` を返します:

```python
# yfinance_adapter.py
def _fetch_from_yfinance(self, ticker):
    try:
        yf_ticker = retry_on_rate_limit(...)
        info = yf_ticker.info
    except (RequestException, KeyError, ValueError, TypeError):
        logger.warning("Failed to fetch data for %s", ticker.symbol)
        return FinancialSnapshot()  # 全フィールド None
```

**理由**: 約4,000銘柄を順次処理するため、1銘柄の API エラーでパイプライン全体が停止するのは不適切。
`None` フィールドはスコアリング時に0点として扱われ、自然と順位が下がります。

### EDINET のフォールバック

```python
# edinet_eval_provider.py
def check_accounting_fraud(self, ticker):
    if self._edinet_client is None:      # API キー未設定
        return CheckStatus.NEEDS_REVIEW
    try:
        ...
    except requests.exceptions.RequestException:
        return CheckStatus.NEEDS_REVIEW  # API エラー時も安全に
```

`NEEDS_REVIEW` は Gate1 の通過判定で FAIL 扱いにならないため、
API 障害時も銘柄が不当に REJECT されることはありません。

---

## ファイル構成

```
shared/
├── retry.py                       # 指数バックオフリトライ

market_data/infrastructure/
├── cache.py                       # JSON ファイルキャッシュ (24h TTL)
├── jpx_stock_list.py              # JPX Excel ダウンロード
└── yfinance_adapter.py            # yfinance 財務データ取得

evaluation/infrastructure/
├── edinet_client.py               # EDINET API v2 クライアント
├── edinet_eval_provider.py        # EDINET データプロバイダ
├── yfinance_eval_provider.py      # yfinance データプロバイダ
└── stub_provider.py               # スタブ (全てデフォルト値)
```
