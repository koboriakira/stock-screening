# Stock Screener

## プロジェクト概要

小型バリュー株スクリーニングシステム（JPX市場対象）。
DDD + TDD で開発しており、Phase 3（実データ接続）まで完了。

## コマンド

```bash
# テスト実行
uv run pytest

# リント
uv run ruff check src/ tests/

# フォーマット
uv run ruff format src/ tests/

# スクリーニング（銘柄抽出）
uv run stock-screener screen --top 30 --output result.csv
uv run stock-screener screen --test   # テストモード: 5銘柄のみ

# 評価（3ゲート判定）
uv run stock-screener evaluate --input result.csv
uv run stock-screener evaluate --input result.csv --output eval.csv

# ポートフォリオ管理
uv run stock-screener record-buy --ticker 4486.T --price 675 --shares 100 --date 2026-02-26
uv run stock-screener record-sell --ticker 4486.T --price 900 --reason "利確"

# 銘柄分析データ
uv run stock-screener save-analysis --ticker 4486.T --file analysis.md
uv run stock-screener show-analysis                    # 全銘柄一覧
uv run stock-screener show-analysis --ticker 4486.T    # 詳細表示

# 日次モニタリング（exit判定 + 分析アラート）
uv run stock-screener monitor --skip-calendar

# 日次レポート（monitor + watchlist-check + サマリー生成）
uv run stock-screener daily-report --skip-calendar
uv run stock-screener daily-report --skip-calendar --notify  # Slack送信
```

## 開発ルール

- TDD サイクル: テスト → 実装 → テスト通過 → リファクタリング → リント → コミット
- 単機能ごとにコミットすること
- コミットメッセージは日本語の本文 + 英語の prefix（feat/fix/refactor/test/docs）

## アーキテクチャ

DDD で 4つの境界づけられたコンテキストに分割。

```
src/stock_screener/
├── shared/          # 値オブジェクト（Ticker, Money, Percentage）、設定値
├── market_data/     # JPX銘柄リスト取得、yfinance での財務データ取得
├── discovery/       # ハードフィルタ → ソフトフィルタ → スコアリング
├── evaluation/      # Gate1(致命的欠陥) → Gate2(カタリスト) → Gate3(バリュエーション)
├── timing/          # エントリー/エグジット判定、ポートフォリオ管理
├── monitoring/      # 日次モニタリング、ウォッチリスト、銘柄分析アラート
└── cli.py
```

### データプロバイダの継承チェーン

```
StubEvaluationDataProvider           # 全メソッド NEEDS_REVIEW / None
  └─ YFinanceEvaluationDataProvider  # earningsGrowth, PER percentile を実装
       └─ EdinetEvaluationDataProvider  # 不正会計チェック, 継続企業チェック を実装
```

新しいデータソースを追加する際は、最下位のプロバイダを継承して該当メソッドをオーバーライドする。

### Gate 判定ロジック

- **Gate1**: すべて FAIL でなければ通過（1つでも FAIL → Gate 不通過）
- **Gate2**: 1つ以上 PASS があれば通過
- **Gate3**: 常に通過（情報提供のみ）
- **最終判定**: Gate1 FAIL → REJECT / Gate2 FAIL → WATCHLIST / 両方 PASS → INVEST

## 環境変数

| 変数名 | 説明 |
|--------|------|
| `EDINET_API_KEY` | EDINET API キー。未設定でも動作する（Gate1 チェックが NEEDS_REVIEW になる） |
| `SLACK_BOT_TOKEN` | Slack Bot Token。未設定の場合は通知をスキップする |

## 未実装のチェック項目（スタブのまま）

以下は対応するデータソースが未接続のため、NEEDS_REVIEW を返す。

| ID | 説明 | 必要なデータソース |
|----|------|-------------------|
| 1-5 | 信用倍率 | JPX 信用取引残高データ or Kabutan |
| 2A-1 | 四半期進捗率改善 | TDnet / EDINET 四半期報告書 |
| 2A-3 | 上方修正実績 | TDnet 業績修正データ |
| 2B-2 | 自社株買い | EDINET / TDnet 自己株取得データ |

## 主要な設定値（shared/config.py）

- ハードフィルタ: 時価総額 50〜500億円、売買代金 500万円以上
- ソフトフィルタ: PER 50倍以下、自己資本比率 20%以上
- スコアリング重み: 割安度 40%、クオリティ 30%、モメンタム 30%
- Gate 閾値: 信用倍率 < 5.0、営業利益成長率 >= 20%、PER パーセンタイル <= 25%
