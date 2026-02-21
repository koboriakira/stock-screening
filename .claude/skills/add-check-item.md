# 新しいチェック項目の追加

## 概要

評価パイプラインに新しいチェック項目を追加する手順。

## 手順

### 1. EvaluationDataProvider にメソッドを追加

`src/stock_screener/evaluation/domain/data_provider.py` の Protocol にメソッドを追加する。

```python
class EvaluationDataProvider(Protocol):
    def new_method(self, ticker: Ticker) -> SomeType | None: ...
```

### 2. StubEvaluationDataProvider にデフォルト実装を追加

`src/stock_screener/evaluation/infrastructure/stub_provider.py` に追加。
- CheckStatus を返すメソッド → `CheckStatus.NEEDS_REVIEW`
- 数値を返すメソッド → `None`
- bool を返すメソッド → `None`

### 3. Gate ファイルにチェックロジックを追加

該当する Gate ファイルに `_check_xxx` メソッドを追加し、`evaluate()` の checks リストに含める。

- `gate1_fatal_flaw.py`: FAIL が1つでもあると Gate 不通過
- `gate2_catalyst.py`: PASS が1つ以上あれば Gate 通過
- `gate3_valuation.py`: 常に通過（情報提供のみ）

### 4. テストを書く

- Gate のテスト: `tests/evaluation/test_gate{N}_xxx.py`
- Provider のテスト: `tests/evaluation/test_{provider_name}.py`

### 5. 実データプロバイダにオーバーライドを実装

継承チェーンの適切なプロバイダでメソッドをオーバーライドする。

```
StubProvider → YFinanceProvider → EdinetProvider
```

データソースに応じてどのプロバイダに実装するかを決める:
- yfinance で取得可能 → `YFinanceEvaluationDataProvider`
- EDINET API で取得可能 → `EdinetEvaluationDataProvider`
- 新しいデータソースが必要 → 新しいプロバイダクラスを作成して最下位に継承

### 6. TDD サイクル

```
テスト作成 → 実装 → テスト通過 → リファクタリング → リント → コミット
```

```bash
uv run pytest tests/evaluation/test_xxx.py -v   # 対象テスト
uv run pytest                                     # 全テスト
uv run ruff check src/ tests/                     # リント
```
