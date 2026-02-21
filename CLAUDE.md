# Stock Screener

## プロジェクト概要
小型バリュー株スクリーニングシステム (Phase 1: JPX市場)

## 開発ルール
- `uv run pytest` でテスト実行
- `uv run ruff check src/ tests/` でリント
- `uv run ruff format src/ tests/` でフォーマット
- TDD: テスト -> 実装 -> テスト通過 -> リファクタリング -> リント -> コミット

## アーキテクチャ
- DDD (shared, market_data, discovery の3コンテキスト)
- src/stock_screener/ 配下にソースコード
- tests/ 配下にテスト

## CLI実行
- `uv run stock-screener screen --top 30 --output result.csv`
- `uv run stock-screener screen --test` (テストモード: 5銘柄)
