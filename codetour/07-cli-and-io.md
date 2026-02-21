# CodeTour: CLI コマンドと入出力仕様

## エントリーポイント

```python
# cli.py
[project.scripts]
stock-screener = "stock_screener.cli:main"
```

`uv run stock-screener` で実行。`main()` が argparse でサブコマンドを解釈します。

---

## サブコマンド一覧

### `screen` — スクリーニング実行

```bash
# 基本実行 (上位30銘柄、キャッシュ有効)
uv run stock-screener screen

# オプション指定
uv run stock-screener screen --top 50 --output result.csv
uv run stock-screener screen --test           # テストモード (5銘柄のみ)
uv run stock-screener screen --no-cache       # キャッシュ無効
uv run stock-screener screen --verbose        # 詳細ログ
```

| オプション | デフォルト | 説明 |
|---|---|---|
| `--top N` | 30 | 上位 N 銘柄を出力 |
| `--output PATH` | `~/.local/share/stock-screener/results/YYYY-MM-DD.csv` | CSV 出力先 |
| `--test` | off | テストモード (5銘柄のみ処理) |
| `--no-cache` | off | yfinance キャッシュを無効化 |
| `--verbose` | off | DEBUG レベルのログを出力 |

### `evaluate` — 3-Gate 評価実行

```bash
# スクリーニング結果を評価
uv run stock-screener evaluate --input result.csv

# 評価結果を CSV に出力
uv run stock-screener evaluate --input result.csv --output eval.csv
```

| オプション | 必須 | 説明 |
|---|---|---|
| `--input PATH` | Yes | スクリーニング結果 CSV のパス |
| `--output PATH` | No | 評価結果 CSV の出力先 |

---

## screen の実行フロー

```
main()
  ↓ args.command == "screen"
_run_screen(args)
  ├─ JpxStockListFetcher.fetch()         → JPX 銘柄リスト取得
  ├─ Universe.from_jpx_data()            → ユニバース生成
  ├─ (--test なら universe.limit(5))
  ├─ YFinanceSecurityRepository          → 財務データ取得 (進捗表示付き)
  ├─ ScreeningService.execute()          → フィルタ + スコアリング
  ├─ _print_result()                     → ターミナル出力
  └─ _write_csv()                        → CSV ファイル出力
```

### 進捗表示

財務データ取得中は stderr にインライン進捗を表示:

```
  [150/3800] 3.9% 7203.T     経過02:30 残62:05
```

- `[現在/全体]` 件数
- パーセンテージ
- 処理中のティッカー
- 経過時間と推定残り時間

---

## evaluate の実行フロー

```
main()
  ↓ args.command == "evaluate"
_run_evaluate(args)
  ├─ CSV 読み込み → EvaluationTarget.from_csv_row()
  ├─ _build_eval_provider()              → Provider 選択
  ├─ EvaluationService.execute()         → 3-Gate 評価
  ├─ _print_evaluation()                 → ターミナル出力
  └─ (--output があれば) _write_evaluation_csv()
```

### Provider 選択ロジック

```python
def _build_eval_provider():
    edinet_api_key = os.environ.get("EDINET_API_KEY")
    if edinet_api_key:
        return EdinetEvaluationDataProvider(edinet_client=EdinetClient(api_key=...))
    return YFinanceEvaluationDataProvider()
```

---

## 出力フォーマット

### screen のターミナル出力

```
================================================================================
スクリーニング結果 (2024-01-15 09:30 UTC)
ユニバース: 3800 → ハードフィルタ後: 1200 → ソフトフィルタ後: 800
================================================================================
順位 ティッカー     銘柄名                  総合   割安     質   変化
--------------------------------------------------------------------------------
   1 1234.T     サンプル株式会社          72.5   85.0   60.0   55.0
   2 5678.T     テスト工業               68.3   70.0   65.0   62.0
   ...
```

### screen の CSV 出力

| カラム | 説明 |
|---|---|
| `rank` | 順位 |
| `ticker` | ティッカー (例: `7203.T`) |
| `company_name` | 企業名 |
| `sector` | セクター |
| `total_score` | 総合スコア |
| `value_score` | 割安スコア |
| `quality_score` | 質スコア |
| `momentum_score` | 変化スコア |
| `per` | PER |
| `pbr` | PBR |
| `roe` | ROE |
| `market_cap` | 時価総額 |

### evaluate のターミナル出力

**一覧表**:
```
================================================================================
評価結果
================================================================================
順位 ティッカー     銘柄名                  判定          Gate1    Gate2    Gate3
--------------------------------------------------------------------------------
   1 1234.T     サンプル株式会社          INVEST       PASS     PASS     PASS
   2 5678.T     テスト工業               WATCHLIST    PASS     FAIL     PASS
```

**詳細ビュー** (各銘柄ごと):
```
--- 1234.T (サンプル株式会社) ---
  Gate1: 致命的欠陥:
    [?] 1-1: 過去3年以内に不正会計・行政処分がないか
    [?] 1-2: 継続企業の前提に関する注記がないか
    [o] 1-5: 信用倍率チェック (信用倍率: 2.3)
  Gate2: カタリスト:
    [o] 2A-2: 営業利益予想成長率 (成長率: 25.0%)
    [x] 2B-2: 自社株買い (自社株買いなし)
    ...
```

チェック記号:
- `[o]` = PASS
- `[x]` = FAIL
- `[?]` = NEEDS_REVIEW

### evaluate の CSV 出力

| カラム | 説明 |
|---|---|
| `rank` | 順位 (discovery での順位) |
| `ticker` | ティッカー |
| `company_name` | 企業名 |
| `verdict` | 判定 (invest / watchlist / reject) |
| `gate1` | Gate1 結果 (PASS / FAIL) |
| `gate2` | Gate2 結果 |
| `gate3` | Gate3 結果 |
| `score_total` | スクリーニングスコア |

---

## デフォルトの出力先

```python
DEFAULT_DATA_DIR = Path.home() / ".local" / "share" / "stock-screener" / "results"
# → ~/.local/share/stock-screener/results/2024-01-15.csv
```

`--output` を省略した場合、実行日付をファイル名とした CSV がこのディレクトリに保存されます。
ディレクトリは自動作成されます。

---

## screen → evaluate のワークフロー

```bash
# Step 1: スクリーニング
uv run stock-screener screen --top 30 --output /tmp/screen.csv

# Step 2: 評価 (スクリーニング結果を入力)
uv run stock-screener evaluate --input /tmp/screen.csv --output /tmp/eval.csv
```

screen の CSV 出力が evaluate の入力になります。
`EvaluationTarget.from_csv_row()` が CSV 行を読み取り、評価対象に変換します。

この設計により、screen と evaluate を **異なるタイミングで独立に実行** できます。
例えば、前日のスクリーニング結果を翌日に評価する、といった使い方が可能です。
