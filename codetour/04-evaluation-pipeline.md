# CodeTour: 3-Gate 評価パイプライン

## 概要

`evaluate` コマンドは、スクリーニング上位銘柄を **3段階のゲート** で精査し、
最終的に **INVEST / WATCHLIST / REJECT** の判定を下します。

```
EvaluationTarget (スクリーニング結果から変換)
  ↓
Gate1: 致命的欠陥チェック
  │ FAIL → REJECT (Gate2/3 はスキップ)
  │ PASS ↓
Gate2: カタリストチェック
  │ FAIL → WATCHLIST
  │ PASS ↓
Gate3: バリュエーション健全性
  │ (常に通過 — 情報提供のみ)
  ↓
Verdict: INVEST / WATCHLIST / REJECT
```

---

## 判定ロジック (値オブジェクト)

### CheckStatus

個別チェック項目の3状態:

```python
class CheckStatus(Enum):
    PASS = "pass"           # 問題なし
    FAIL = "fail"           # 問題あり
    NEEDS_REVIEW = "needs_review"  # データ不足、手動確認推奨
```

### GateResult — ゲートごとの通過判定

各ゲートは **異なる通過条件** を持ちます:

| ゲート | 通過条件 | 設計意図 |
|---|---|---|
| Gate1 | 全チェックが FAIL でない | 致命的問題が1つでもあれば除外 |
| Gate2 | 1つ以上が PASS | カタリストが何か1つあれば十分 |
| Gate3 | 常に通過 | 情報提供のみ、判定には影響しない |

```python
# check.py
class GateResult:
    @classmethod
    def for_gate1(cls, gate_name, checks):
        passed = all(c.status != CheckStatus.FAIL for c in checks)

    @classmethod
    def for_gate2(cls, gate_name, checks):
        passed = any(c.status == CheckStatus.PASS for c in checks)

    @classmethod
    def for_gate3(cls, gate_name, checks):
        return cls(gate_name=gate_name, checks=checks, passed=True)
```

### Verdict — 最終判定

```python
def determine_verdict(gate1, gate2, gate3) -> Verdict:
    if not gate1.passed:
        return Verdict.REJECT      # 致命的欠陥あり → 投資不可
    if not gate2.passed:
        return Verdict.WATCHLIST   # カタリスト不足 → 監視継続
    return Verdict.INVEST          # 全ゲート通過 → 投資候補
```

---

## Gate1: 致命的欠陥 (`FatalFlawGate`)

投資に致命的な問題がないかを検証します。1つでも FAIL なら即座に REJECT。

| チェック ID | 内容 | FAIL 条件 | データソース |
|---|---|---|---|
| 1-1 | 不正会計・行政処分 | 過去3年以内に訂正報告書あり | EDINET API |
| 1-2 | 継続企業の前提注記 (GC) | GC 注記あり | EDINET API |
| 1-5 | 信用倍率 | 5.0倍以上 | yfinance (将来実装) |

**短絡評価**: Gate1 が FAIL の場合、Gate2/Gate3 はスキップされます。
API コストの節約と、REJECT 確定銘柄への無駄な処理を回避するためです。

```python
# service.py
def _evaluate_single(self, target):
    gate1_result = self._gate1.evaluate(target, self._provider)
    if not gate1_result.passed:
        # Gate2/3 は空のまま REJECT を返す
        empty_gate2 = GateResult.for_gate2("Gate2: カタリスト", [])
        empty_gate3 = GateResult.for_gate3("Gate3: バリュエーション", [])
        ...
```

---

## Gate2: カタリスト (`CatalystGate`)

株価上昇の触媒 (カタリスト) が存在するかを検証します。
1つでも PASS があれば通過 — **OR 条件** です。

| チェック ID | 内容 | PASS 条件 | データソース |
|---|---|---|---|
| 2A-1 | 四半期進捗率改善 | 改善幅 ≥ 5% | Stub (将来実装) |
| 2A-2 | 営業利益予想成長率 | ≥ 20% | yfinance (`earningsGrowth`) |
| 2A-3 | 上方修正実績 | 直近1年以内に修正あり | Stub (将来実装) |
| 2B-2 | 自社株買い | 実施/発表あり | Stub (将来実装) |
| 2D-2 | TOB/MBO 構造 | PBR < 1.0 かつ ネットキャッシュ比率 ≥ 30% | FinancialSnapshot |

2D-2 は外部データ取得不要で、スクリーニング時の `FinancialSnapshot` から判定できます。

---

## Gate3: バリュエーション健全性 (`ValuationSanityGate`)

バリュエーション面の参考情報を提供します。**常に通過** — 判定への影響はなし。

| チェック ID | 内容 | PASS 条件 | データソース |
|---|---|---|---|
| 3-2 | PER 5年レンジ下位25% | パーセンタイル ≤ 25% | yfinance (過去5年月次データ) |
| 3-3 | ネットキャッシュ比率 | ≥ 30% | FinancialSnapshot |

### PER パーセンタイルの算出

過去5年の月次株価と年次 EPS から各月の理論 PER を算出し、
現在の PER が全体のどの位置にあるかをパーセンタイルで表します。

```python
# yfinance_eval_provider.py の compute_per_percentile()
#
# 例: 過去5年で PER が 8〜25 の範囲で推移
#     現在 PER = 10 → 下位20%に位置 → パーセンタイル = 20.0
```

---

## EvaluationTarget — コンテキスト間の ACL

`evaluation` コンテキストは `discovery` の `Candidate` を直接参照しません。
`EvaluationTarget` が **腐敗防止層 (ACL)** として機能します。

```python
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
        # discovery → evaluation の変換

    @classmethod
    def from_csv_row(cls, row: dict[str, str]) -> EvaluationTarget:
        # CSV ファイル経由でも生成可能
```

2つの生成経路:
1. **メモリ内**: `screen` → `evaluate` を連続実行する場合 (`from_candidate`)
2. **ファイル経由**: CSV を介して疎結合に実行する場合 (`from_csv_row`)

---

## EvaluationService — パイプラインオーケストレーション

```python
class EvaluationService:
    def __init__(self, provider: EvaluationDataProvider):
        self._provider = provider
        self._gate1 = FatalFlawGate()
        self._gate2 = CatalystGate()
        self._gate3 = ValuationSanityGate()

    def execute(self, targets: list[EvaluationTarget]) -> list[EvaluationReport]:
        return [self._evaluate_single(target) for target in targets]
```

`provider` はコンストラクタ注入で渡されるため、テスト時はスタブ、本番は yfinance + EDINET と切り替え可能です。

---

## EvaluationReport — 最終出力

```python
@dataclass(frozen=True)
class EvaluationReport:
    target: EvaluationTarget
    gate1: GateResult          # Gate1 の結果 (checks + passed)
    gate2: GateResult          # Gate2 の結果
    gate3: GateResult          # Gate3 の結果
    verdict: Verdict           # INVEST / WATCHLIST / REJECT
    evaluated_at: datetime     # 評価日時 (UTC)
```

CLI は各レポートを一覧表と詳細ビューで出力します (→ [07-cli-and-io.md](./07-cli-and-io.md))。
