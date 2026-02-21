# CodeTour: データ取得からスクリーニングまでの流れ

## パイプライン全体像

`screen` コマンド実行時のデータフローは以下の4ステップです。

```
Step 1: JPX 銘柄リスト取得
  ↓ JpxStockListFetcher.fetch()
Step 2: Universe 生成
  ↓ Universe.from_jpx_data()
Step 3: 財務データ取得
  ↓ YFinanceSecurityRepository.get_financial_snapshot()
Step 4: スクリーニング実行
  ↓ ScreeningService.execute()
  → ScreeningResult (候補銘柄 + 統計)
```

---

## Step 1: JPX 銘柄リスト取得

`JpxStockListFetcher` が JPX 公開の Excel ファイルをダウンロードし、全上場銘柄を取得します。

```python
# market_data/infrastructure/jpx_stock_list.py
JPX_URL = "https://www.jpx.co.jp/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_j.xls"

class JpxStockListFetcher:
    def fetch(self, url: str = JPX_URL) -> list[dict]:
        df = pd.read_excel(url)
        # → [{"ticker": "7203", "company_name": "トヨタ自動車", "sector": "輸送用機器", "market": "プライム"}, ...]
```

**データ正規化**:
- コード列の `.0` を除去して整数化
- `130A` 等の英字混在コードはスキップ (数字4桁のみ)
- 市場名は `（内国株式）` 等のサフィックスを除去

---

## Step 2: Universe 生成

`Universe` は JPX データから `Security` オブジェクトのリストを生成します。

```python
# discovery/domain/universe.py
class Universe:
    securities: list[Security]

    @classmethod
    def from_jpx_data(cls, jpx_data: list[dict]) -> Universe:
        securities = [
            Security(
                ticker=Ticker(item["ticker"]),
                company_name=item["company_name"],
                sector=item["sector"],
            )
            for item in jpx_data
        ]
        return cls(securities=securities)
```

この時点では `Security.financial_snapshot` はデフォルト値 (全フィールド `None`) です。
テストモードでは `universe.limit(5)` で先頭5銘柄に制限します。

---

## Step 3: 財務データ取得

CLI が各銘柄の `financial_snapshot` を yfinance から取得して設定します。

```python
# cli.py の _run_screen() 内
repo = YFinanceSecurityRepository(cache=cache)
for sec in universe.securities:
    snap = repo.get_financial_snapshot(sec.ticker)
    sec.financial_snapshot = snap  # ← ミュータブルなフィールドに代入
```

`YFinanceSecurityRepository` は以下の13指標を取得します:

| # | フィールド | データソース | 用途 |
|---|---|---|---|
| 1 | `market_cap` | `info.marketCap` | ハードフィルタ |
| 2 | `per` | `info.forwardPE` or `trailingPE` | ソフトフィルタ, スコアリング |
| 3 | `pbr` | `info.priceToBook` | スコアリング |
| 4 | `roe` | `info.returnOnEquity` | スコアリング |
| 5 | `operating_margin` | `info.operatingMargins` | スコアリング |
| 6 | `revenue_growth` | `info.revenueGrowth` | ソフトフィルタ, スコアリング |
| 7 | `operating_profit_growth` | 財務諸表から算出 | スコアリング |
| 8 | `equity_ratio` | 貸借対照表から算出 | ソフトフィルタ |
| 9 | `dividend_yield` | `info.dividendYield` | スコアリング |
| 10 | `high_52w_discount` | 株価から算出 | スコアリング |
| 11 | `net_cash_ratio` | 現金-負債/総資産 | スコアリング |
| 12 | `current_price` | `info.currentPrice` | 算出用 |
| 13 | `avg_trading_value` | 株価×出来高 | ハードフィルタ |

**算出ロジック** (yfinance の生データから導出):
- `high_52w_discount` = (52週高値 - 現在値) / 52週高値
- `avg_trading_value` = 現在値 × 平均出来高
- `net_cash_ratio` = (総現金 - 総負債) / 総資産
- `equity_ratio` = 自己資本 / 総資産
- `operating_profit_growth` = (最新営業利益 - 前期営業利益) / |前期営業利益|

---

## Step 4: スクリーニング実行

`ScreeningService.execute()` が3段階パイプラインを実行します。

```python
# discovery/service.py
class ScreeningService:
    def execute(self, securities: list[Security], top_n: int = 30) -> ScreeningResult:
        # (1) ハードフィルタ
        after_hard = self._hard_filter.apply(securities)
        # (2) ソフトフィルタ
        after_soft = self._soft_filter.apply(after_hard)
        # (3) スコアリング + ソート
        scored = [(sec, CompositeScorer.score(sec.financial_snapshot)) for sec in after_soft]
        scored.sort(key=lambda x: x[1].total, reverse=True)
        # 上位N件を Candidate に変換
        candidates = [Candidate(security=sec, score=score, rank=i+1) for ...]
        return ScreeningResult(candidates=candidates, ...)
```

### (1) ハードフィルタ

**絶対条件** で即座に除外。フィルタ条件は `shared/config.py` で定義:

| 条件 | 閾値 | 意味 |
|---|---|---|
| 時価総額 (下限) | 50億円 | マイクロキャップ除外 |
| 時価総額 (上限) | 500億円 | 大型株除外 |
| 平均売買代金 | 500万円/日以上 | 流動性確保 |
| 除外セクター | 医薬品, 不動産業 | 特殊業種を除外 |

### (2) ソフトフィルタ

**緩やかな条件** で投資対象として妥当な範囲に絞り込み:

| 条件 | 閾値 | 意味 |
|---|---|---|
| PER 上限 | 50倍 | 超高PER除外 |
| 自己資本比率 | 20%以上 | 財務健全性の最低基準 |
| 売上高成長率 | -30%以上 | 急激な業績悪化を除外 |

**None 安全**: 各指標が `None` の場合は条件をスキップ (除外しない)。

### (3) スコアリング → ソート

ソフトフィルタ通過銘柄に対して `CompositeScorer.score()` でスコアを算出し、
`total` の降順でソートして上位 `top_n` 件を抽出します。

---

## 出力: ScreeningResult

```python
@dataclass(frozen=True)
class ScreeningResult:
    candidates: list[Candidate]    # 候補銘柄リスト (ランク付き)
    total_universe: int            # ユニバース全体数
    after_hard_filter: int         # ハードフィルタ通過数
    after_soft_filter: int         # ソフトフィルタ通過数
    timestamp: datetime            # 実行日時 (UTC)
```

結果は CSV ファイルとして出力され、`evaluate` コマンドの入力として使用できます。

---

## データフロー図 (まとめ)

```
JPX Excel
  ↓ JpxStockListFetcher.fetch()
list[dict]  ← {ticker, company_name, sector, market}
  ↓ Universe.from_jpx_data()
list[Security]  ← financial_snapshot = None
  ↓ YFinanceSecurityRepository.get_financial_snapshot()
list[Security]  ← financial_snapshot = 13指標
  ↓ HardFilter.apply()
list[Security]  ← 時価総額・流動性・セクターで除外
  ↓ SoftFilter.apply()
list[Security]  ← PER・自己資本比率・成長率で絞り込み
  ↓ CompositeScorer.score() + sort
list[Candidate]  ← スコア + ランク付き
  ↓ CSV 出力
result.csv
```
