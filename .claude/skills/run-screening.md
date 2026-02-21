# スクリーニングの実行

## 概要

スクリーニング（銘柄抽出）と評価（3ゲート判定）の実行手順。

## スクリーニング（screen コマンド）

JPX 全銘柄からフィルタリングとスコアリングで上位銘柄を抽出する。

```bash
# 上位30銘柄を抽出
uv run stock-screener screen --top 30 --output result.csv

# テストモード（5銘柄のみ、動作確認用）
uv run stock-screener screen --test

# 上位50銘柄
uv run stock-screener screen --top 50 --output result.csv
```

**注意**: 全銘柄モードでは yfinance から約4000銘柄分のデータを取得するため、数十分かかる。

### 出力 CSV のカラム

```
rank, ticker, company_name, sector, total_score, value_score, quality_score, momentum_score, per, pbr, roe, market_cap
```

## 評価（evaluate コマンド）

スクリーニング結果に対して 3ゲート評価を行う。

```bash
# 画面に結果を表示
uv run stock-screener evaluate --input result.csv

# CSV にも出力
uv run stock-screener evaluate --input result.csv --output eval.csv
```

### EDINET API を使う場合

環境変数 `EDINET_API_KEY` を設定すると、Gate1 の不正会計チェック（1-1）が実データで判定される。

```bash
export EDINET_API_KEY="your-api-key"
uv run stock-screener evaluate --input result.csv
```

未設定でも動作する（Gate1 チェックが NEEDS_REVIEW になる）。

### 評価結果の読み方

- `[o]` = PASS
- `[x]` = FAIL
- `[?]` = NEEDS_REVIEW（データ不足のため判定保留）

最終判定:
- **INVEST**: Gate1 通過 & Gate2 通過 → 投資候補
- **WATCHLIST**: Gate1 通過 & Gate2 不通過 → カタリスト待ち
- **REJECT**: Gate1 不通過 → 投資不適格
