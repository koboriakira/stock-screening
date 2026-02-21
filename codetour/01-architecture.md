# CodeTour: DDD アーキテクチャと境界づけられたコンテキスト

## 4つの境界づけられたコンテキスト

本システムは DDD (ドメイン駆動設計) に基づき、4つのコンテキストに分割されています。

```
┌─────────────────────────────────────────────────────────┐
│                       cli.py                            │
│              (オーケストレーション層)                       │
└───────┬──────────────────┬──────────────────┬───────────┘
        │                  │                  │
   ┌────▼────┐      ┌──────▼──────┐    ┌──────▼──────┐
   │discovery│      │ evaluation  │    │ market_data │
   │スクリーニング│   │   評価      │    │ 市場データ    │
   └────┬────┘      └──────┬──────┘    └──────┬──────┘
        │                  │                  │
        └──────────────────┴──────────────────┘
                           │
                    ┌──────▼──────┐
                    │   shared    │
                    │ 共有カーネル  │
                    └─────────────┘
```

## 依存の方向

依存は常に **上から下** に流れます。循環依存はありません。

| コンテキスト | 依存先 |
|---|---|
| `shared` | なし (最下層) |
| `market_data` | `shared` |
| `discovery` | `shared`, `market_data` |
| `evaluation` | `shared`, `market_data`, `discovery` |
| `cli.py` | 全コンテキスト |

## 各コンテキストの責務

### shared (共有カーネル)

全コンテキストが利用する **値オブジェクト** と **設定定数** を提供します。

```
shared/
├── types.py    → Ticker, Money, Percentage (イミュータブルな値オブジェクト)
├── config.py   → HARD_FILTERS, SOFT_FILTERS, SCORING_WEIGHTS 等の定数
└── retry.py    → retry_on_rate_limit() (API レートリミット対応)
```

**設計ポイント**: `Ticker` は frozen dataclass で `code` を内部保持し、
`.symbol` プロパティで `"7203.T"` 形式を返します。4-5桁の数値バリデーション付きです。

### market_data (市場データ)

銘柄情報と財務データの **取得・保持** を担います。

```
domain/
├── FinancialSnapshot  → 13項目の財務指標 (PER, PBR, ROE, 時価総額 等)
├── Security           → ティッカー + 企業名 + セクター + 財務スナップショット
└── SecurityRepository → リポジトリの Protocol 定義

infrastructure/
├── JpxStockListFetcher    → JPX Excel から銘柄リストを取得
├── YFinanceSecurityRepository → yfinance で財務データを取得
└── FileCache              → JSON ファイルキャッシュ (24h TTL)
```

**設計ポイント**: `Security.financial_snapshot` はミュータブルです。
CLI がユニバース生成後に yfinance から取得した snapshot を後から設定するためです。

### discovery (スクリーニング)

銘柄のフィルタリングとスコアリングを担います。

```
domain/
├── Universe     → 全銘柄を保持、JPX データから生成
├── HardFilter   → 絶対条件でのフィルタリング
├── SoftFilter   → 緩やかな条件でのフィルタリング
├── scoring/     → 3軸スコアリング (Value, Quality, Momentum)
└── Candidate    → スコア付き候補銘柄

service/
└── ScreeningService → パイプライン全体を実行
```

**設計ポイント**: フィルタは2段階構成。ハードフィルタで明らかに対象外の銘柄を除外し、
ソフトフィルタで投資対象として妥当な範囲に絞り込みます。

### evaluation (評価)

スクリーニング結果の各銘柄を **3-Gate パイプライン** で精査します。

```
domain/
├── CheckStatus / CheckResult / GateResult → 判定結果の値オブジェクト
├── EvaluationDataProvider  → 外部データ取得の Protocol
├── EvaluationTarget        → discovery → evaluation の ACL (腐敗防止層)
├── Gate1 / Gate2 / Gate3   → 各ゲートのドメインロジック
└── EvaluationReport        → 最終判定 (INVEST / WATCHLIST / REJECT)

infrastructure/
├── StubEvaluationDataProvider     → スタブ (全て NEEDS_REVIEW)
├── YFinanceEvaluationDataProvider → yfinance 実データ
└── EdinetEvaluationDataProvider   → EDINET 実データ

service/
└── EvaluationService → Gate1 → Gate2 → Gate3 のパイプライン実行
```

## コンテキスト間の境界: ACL (腐敗防止層)

`evaluation` コンテキストは `discovery` の `Candidate` を直接参照しません。
代わりに `EvaluationTarget` が ACL として機能し、コンテキスト間の結合を緩やかにしています。

```python
# evaluation/domain/evaluation_target.py
@dataclass(frozen=True)
class EvaluationTarget:
    ticker: Ticker
    company_name: str
    sector: str
    financial_snapshot: FinancialSnapshot
    discovery_rank: int
    score_total: float

    @classmethod
    def from_candidate(cls, candidate: Candidate) -> EvaluationTarget:
        # discovery の Candidate から evaluation の EvaluationTarget に変換
        ...

    @classmethod
    def from_csv_row(cls, row: dict[str, str]) -> EvaluationTarget:
        # CSV からも直接生成可能 (screen → evaluate をファイル経由で疎結合に)
        ...
```

## Protocol ベースの依存性逆転

外部データ取得のインターフェースは `Protocol` (構造的部分型) で定義しています。
Gate1/2/3 は `EvaluationDataProvider` Protocol に依存し、具体的な実装を知りません。

```python
# evaluation/domain/data_provider.py
class EvaluationDataProvider(Protocol):
    def check_accounting_fraud(self, ticker: Ticker) -> CheckStatus: ...
    def get_earnings_growth_forecast(self, ticker: Ticker) -> float | None: ...
    # ... 全8メソッド
```

これにより、テスト時はスタブ、本番は yfinance + EDINET という切り替えが
**コンストラクタ注入** のみで実現できます。
