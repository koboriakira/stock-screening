# CodeTour: システム全体概要

## このドキュメントについて

`codetour/` は stock-screener の実装内容と設計を理解するためのガイドです。
以下の順序で読むことを推奨します。

| # | ファイル | 内容 |
|---|---|---|
| 00 | [overview.md](./00-overview.md) | システム全体概要 (このファイル) |
| 01 | [architecture.md](./01-architecture.md) | DDD アーキテクチャと境界づけられたコンテキスト |
| 02 | [data-pipeline.md](./02-data-pipeline.md) | データ取得からスクリーニングまでの流れ |
| 03 | [scoring.md](./03-scoring.md) | 3軸スコアリングの設計と配点 |
| 04 | [evaluation-pipeline.md](./04-evaluation-pipeline.md) | 3-Gate 評価パイプラインの仕組み |
| 05 | [data-providers.md](./05-data-providers.md) | データプロバイダの継承チェーンと段階的実データ化 |
| 06 | [infrastructure.md](./06-infrastructure.md) | 外部 API 連携・キャッシュ・リトライ機構 |
| 07 | [cli-and-io.md](./07-cli-and-io.md) | CLI コマンドと入出力仕様 |

---

## システムの目的

**小型バリュー株スクリーニングシステム** - JPX (東京証券取引所) 上場の約4,000銘柄から、
割安で質の高い小型株を機械的に選別し、投資判断を支援するツールです。

## 2つの主要機能

### 1. スクリーニング (`screen`)

全銘柄を対象に「ハードフィルタ → ソフトフィルタ → 3軸スコアリング」で上位銘柄を抽出します。

```
JPX 全銘柄 (~4,000)
  ↓ ハードフィルタ: 時価総額・売買代金・セクター
  ↓ ソフトフィルタ: PER・自己資本比率・成長率
  ↓ スコアリング: 割安(40%) + 質(30%) + 変化(30%)
  → 上位30銘柄を CSV 出力
```

### 2. 評価 (`evaluate`)

スクリーニング結果の各銘柄を「3-Gate パイプライン」で深掘り評価します。

```
スクリーニング上位銘柄
  ↓ Gate1: 致命的欠陥 (不正会計・GC注記・信用倍率)
  ↓ Gate2: カタリスト (成長予想・上方修正・自社株買い等)
  ↓ Gate3: バリュエーション (PER水準・ネットキャッシュ)
  → INVEST / WATCHLIST / REJECT の判定
```

## 技術スタック

| 項目 | 技術 |
|---|---|
| 言語 | Python 3.12+ |
| パッケージ管理 | uv |
| 外部データ | yfinance, EDINET API v2 |
| 銘柄リスト | JPX Excel ファイル |
| テスト | pytest (271テスト, カバレッジ98%) |
| リンター | ruff (ALL ルール有効) |
| 設計方針 | DDD, TDD, Protocol ベースの DI |

## ディレクトリ構造

```
src/stock_screener/
├── cli.py                          # CLI エントリーポイント
├── shared/                         # 共有カーネル
│   ├── config.py                   #   設定定数
│   ├── retry.py                    #   リトライユーティリティ
│   └── types.py                    #   値オブジェクト (Ticker, Money, Percentage)
├── market_data/                    # 市場データコンテキスト
│   ├── domain/
│   │   ├── financial_snapshot.py   #   財務スナップショット
│   │   ├── repository.py          #   リポジトリ Protocol
│   │   └── security.py            #   銘柄モデル
│   └── infrastructure/
│       ├── cache.py                #   ファイルキャッシュ (24h TTL)
│       ├── jpx_stock_list.py       #   JPX 銘柄リスト取得
│       └── yfinance_adapter.py     #   yfinance アダプタ
├── discovery/                      # スクリーニングコンテキスト
│   ├── domain/
│   │   ├── candidate.py            #   候補銘柄・結果
│   │   ├── hard_filter.py          #   ハードフィルタ
│   │   ├── soft_filter.py          #   ソフトフィルタ
│   │   ├── universe.py             #   ユニバース
│   │   └── scoring/                #   スコアリング
│   │       ├── __init__.py         #     CompositeScorer
│   │       ├── value_score.py      #     割安スコア
│   │       ├── quality_score.py    #     質スコア
│   │       └── momentum_score.py   #     変化スコア
│   └── service.py                  #   ScreeningService
└── evaluation/                     # 評価コンテキスト
    ├── domain/
    │   ├── check.py                #   CheckStatus, CheckResult, GateResult
    │   ├── data_provider.py        #   EvaluationDataProvider Protocol
    │   ├── evaluation_report.py    #   Verdict, EvaluationReport
    │   ├── evaluation_target.py    #   評価対象 (ACL)
    │   ├── gate1_fatal_flaw.py     #   Gate1: 致命的欠陥
    │   ├── gate2_catalyst.py       #   Gate2: カタリスト
    │   └── gate3_valuation.py      #   Gate3: バリュエーション
    ├── infrastructure/
    │   ├── stub_provider.py        #   スタブ実装
    │   ├── yfinance_eval_provider.py  # yfinance 実装
    │   ├── edinet_client.py        #   EDINET API クライアント
    │   └── edinet_eval_provider.py #   EDINET 実装
    └── service.py                  #   EvaluationService
```

## コード規模

| 区分 | ファイル数 | 行数(概算) |
|---|---|---|
| ソースコード | 28 | ~1,900 |
| テストコード | 20 | ~2,600 |
| 合計 | 48 | ~4,500 |
