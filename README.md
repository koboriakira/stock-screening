# Stock Screener

小型バリュー株スクリーニングシステム。JPX（東証）上場銘柄を対象に、定量的なフィルタリングとスコアリングでバリュー株候補を抽出し、3段階のゲート評価で投資判断を支援します。

## セットアップ

```bash
# 依存関係のインストール
uv sync

# テスト実行
uv run pytest

# リント
uv run ruff check src/ tests/
```

### 環境変数（任意）

| 変数名 | 説明 | 必須 |
|--------|------|------|
| `EDINET_API_KEY` | EDINET API のサブスクリプションキー。設定すると Gate1 の不正会計チェックが実データ化される | No |

EDINET API キーは [EDINET API 利用申請ページ](https://disclosure.edinet-fsa.go.jp/) から無料で取得できます。

## 使い方

### 1. スクリーニング（銘柄の絞り込み）

JPX 全銘柄からハードフィルタ・ソフトフィルタ・スコアリングで上位銘柄を抽出します。

```bash
# 上位30銘柄を抽出し CSV に出力
uv run stock-screener screen --top 30 --output result.csv

# テストモード（5銘柄のみ）
uv run stock-screener screen --test
```

**スクリーニングの流れ:**

```
JPX全銘柄 → ハードフィルタ → ソフトフィルタ → スコアリング → 上位N銘柄
```

- **ハードフィルタ**: 時価総額 50〜500億円、1日平均売買代金 500万円以上、除外セクター（医薬品・不動産業）
- **ソフトフィルタ**: PER 50倍以下、自己資本比率 20%以上、売上高成長率 -30%以上
- **スコアリング**: 割安度(40%) + クオリティ(30%) + モメンタム(30%) の加重平均

### 2. 評価（3ゲート判定）

スクリーニング結果に対して 3段階のゲート評価を行い、INVEST / WATCHLIST / REJECT を判定します。

```bash
# スクリーニング結果を評価
uv run stock-screener evaluate --input result.csv

# 評価結果を CSV に出力
uv run stock-screener evaluate --input result.csv --output eval.csv
```

**ゲート判定ロジック:**

| ゲート | 目的 | 通過条件 |
|--------|------|----------|
| Gate1: 致命的欠陥 | 投資不適格の排除 | すべてのチェックが FAIL でないこと |
| Gate2: カタリスト | 株価上昇の材料確認 | 1つ以上のチェックが PASS |
| Gate3: バリュエーション | 割安性の確認 | 常に通過（情報提供のみ） |

**最終判定:**
- Gate1 FAIL → **REJECT**
- Gate1 PASS & Gate2 FAIL → **WATCHLIST**
- Gate1 PASS & Gate2 PASS → **INVEST**

### チェック項目一覧

| ID | ゲート | 説明 | データソース | 実装状況 |
|----|--------|------|------------|----------|
| 1-1 | Gate1 | 不正会計・行政処分（過去3年） | EDINET | 実装済 |
| 1-2 | Gate1 | 継続企業の前提 | EDINET | 部分実装（有報存在確認のみ） |
| 1-5 | Gate1 | 信用倍率 < 5.0倍 | - | 未実装 |
| 2A-1 | Gate2 | 四半期進捗率改善 >= 5% | - | 未実装 |
| 2A-2 | Gate2 | 営業利益予想成長率 >= 20% | yfinance | 実装済 |
| 2A-3 | Gate2 | 上方修正実績（直近1年） | - | 未実装 |
| 2B-2 | Gate2 | 自社株買い | - | 未実装 |
| 2D-2 | Gate2 | TOB/MBO構造（PBR<1.0 & ネットキャッシュ比率>=30%） | yfinance | 実装済 |
| 3-2 | Gate3 | PER 5年レンジ下位25% | yfinance | 実装済 |
| 3-3 | Gate3 | ネットキャッシュ比率 >= 30% | yfinance | 実装済 |

## アーキテクチャ

DDD（ドメイン駆動設計）で 4つの境界づけられたコンテキストに分割しています。

```
src/stock_screener/
├── shared/          # 共有カーネル（Ticker, Money, Percentage 等の値オブジェクト）
├── market_data/     # 市場データコンテキスト（JPX銘柄リスト、yfinance連携）
├── discovery/       # 発見コンテキスト（フィルタリング、スコアリング）
├── evaluation/      # 評価コンテキスト（3ゲートパイプライン）
└── cli.py           # CLIエントリポイント
```

### データプロバイダの継承チェーン

```
StubEvaluationDataProvider        ← 全メソッド NEEDS_REVIEW / None
  └─ YFinanceEvaluationDataProvider  ← 2A-2, 3-2 を実データ化
       └─ EdinetEvaluationDataProvider  ← 1-1, 1-2 を実データ化
```

`EDINET_API_KEY` 環境変数の有無で自動的にプロバイダが切り替わります。

## 開発

```bash
# テスト
uv run pytest

# リント
uv run ruff check src/ tests/

# フォーマット
uv run ruff format src/ tests/
```

テスト駆動開発（TDD）で進めています。詳細は `CLAUDE.md` を参照してください。
