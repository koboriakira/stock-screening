# 要件転換ドラフト: adapter-stock から呼ばれる株式情報取得ハブ

- status: v1（2026-07-12 未決事項へのユーザー決定を反映）
- created: 2026-07-12
- 出典調査: 本リポジトリ全72ファイル棚卸し / グローバル adapter-*/port-* スキル14件の規約抽出 / 利用側ユースケース調査（Issue koboriakira/tasks#40・Vault・Task・skills）

## 1. 背景と再定義

### 従来の位置づけ

小型バリュー株スクリーニングシステム。発掘（discovery）→ 評価（evaluation）→ タイミング（timing）→ 保有モニタリング（monitoring）を一気通貫で担う「投資運用アプリケーション」だった。

### 新しい位置づけ

**グローバルスキル `adapter-stock` から呼び出される「株式情報取得ハブ」**。本リポジトリはその正典実装（バックエンド）となる。

- adapter-stock（`~/.claude/skills/adapter-stock/`、新設）: 呼び出し元スキルとの契約を定義する薄い層
- 本リポジトリ: 外部データソース（yfinance / JPX / EDINET）との会話を安定化し、構造化 JSON を返す決定論的実装

### 転換の動機（調査で確認した事実）

1. **取得ロジックの分散が始まっている**: market-watch リポジトリの `ripple-analysis` / `decision-review` スキルが、株価・出来高を Yahoo Finance chart API（`query1.finance.yahoo.com/v8/finance/chart/`）+ WebFetch で独自取得している。同種の取得実装が今後リポジトリごとに再発明される
2. **本リポジトリには取得資産が既に揃っている**: yfinance アダプタ（リトライ・24h キャッシュ内蔵）、JPX 銘柄リスト、EDINET クライアント、テクニカルシグナル検出（RSI/BB/MACD/出来高/25MA）、JPX 営業日判定
3. **グローバルスキル群に株式情報の入口が存在しない**: `~/.claude/skills/` に株式・投資系の adapter は皆無（調査で確認済み）

## 2. アーキテクチャ（adapter 3層モデルへの位置づけ）

グローバルスキルの層設計規約（adapter = 外部世界との会話の安定化・成果物なし / port = fan-out 時のみ / domain = 成果物と判断を所有）に従う。

```
[呼び出し元（ドメイン側）]
  market-watch: ripple-analysis / decision-review / flash-triage
  対話セッション（銘柄について聞かれたとき）
  将来の投資判断・レポート系スキル
        │  Skill("adapter-stock", args="quote 7203.T") 等
        ▼
[adapter-stock]  ~/.claude/skills/adapter-stock/SKILL.md（新設）
  コマンド→CLI のマッピング、エラー対応表、委譲モデルを定義
        │  uv run --project ~/git/stock-screening stock-screener <cmd> ...
        ▼
[stock-screening リポジトリ = 正典実装]
  取得・計算・キャッシュ・リトライ・JSON 整形
        │
        ▼
[外部データソース]  yfinance / JPX Excel / EDINET API v2 / pandas_market_calendars
```

- **port-stock は作らない**（Rule of Two: 1取得結果を複数ドメインへ自動 fan-out する要求が現れるまで不要）
- **正典の配置**: 「決定論的・繰り返し実行される処理はスクリプト/コードが正典」の規約どおり、取得ロジックの正典は本リポジトリのコード。SKILL.md は契約（何を渡せば何が返るか）だけを持つ

## 3. 機能要件

### 3.1 提供する情報の2分類

| 分類 | 意味 | 例 |
|------|------|-----|
| 一次情報（取得） | 外部ソースの値をそのまま構造化して返す | 株価、出来高、財務スナップショット、銘柄リスト、営業日 |
| 派生情報（計算） | 一次情報からの読み取り専用・決定論的計算 | テクニカルシグナル、スクリーニングスコア、3ゲート評価 |

どちらも「情報取得」であり、ハブのスコープに含める。**判断（買う/売る/見送る）と記録（売買・通知）はスコープ外**（§3.4）。

### 3.2 コマンド仕様（adapter-stock が公開する契約）

| コマンド | 引数・オプション | 返す情報（items の中身） | データソース | キー要否 | 実装状況 |
|---|---|---|---|---|---|
| `quote <ticker>` | | 現在値・前日比・出来高 | yfinance | 不要 | 新規（既存 fetch_market_data を流用） |
| `history <ticker>` | `--period`（既定 3mo）`--interval`（既定 1d） | OHLCV 日足配列 | yfinance | 不要 | 新規 |
| `financials <ticker>` | | FinancialSnapshot 13項目 + data_completeness | yfinance | 不要 | 新規（既存 YFinanceSecurityRepository を流用） |
| `signals <ticker>` | | RSI / BB / MACD / 出来高比 / 25MA乖離 + シグナルレベル（buy_candidate/attention/none） | yfinance + bottom_detector | 不要 | 新規（既存 detect_bottom_signals を流用） |
| `universe` | `--market` 等のフィルタ | JPX 全銘柄リスト（コード・名称・市場・セクター） | JPX Excel | 不要 | 新規（既存 JpxStockListFetcher を流用） |
| `trading-day [date]` | | JPX 営業日判定（`is_trading_day`）+ 翌営業日（`next_trading_day`）+ 寄付・引け時刻（`market_open`/`market_close`、JST、非営業日は `null`） | pandas_market_calendars | 不要 | 実装済み（既存 is_trading_day を流用 + 翌営業日・寄付引け時刻を拡張、koboriakira/stock-screening#2） |
| `large-holdings <ticker>` | `--days`（既定90） | 大量保有報告書（5%ルール、docTypeCode 350/360）の提出日時・提出者名・証券コード（`status`: `ok`/`needs_review`） | EDINET（大量保有報告 + EDINETコードリスト） | 必須（EDINET_API_KEY 未設定時は全件 `status: "needs_review"`） | 実装済み（corporate_events/ 新設、EdinetClient を edinet/ へ移動、koboriakira/stock-screening#3） |
| `earnings-date <ticker>` | | 決算発表予定日（`date`/`company_name`/`fiscal_year`/`fiscal_quarter`、`status`: `ok`/`needs_review`）。**発表予定日のみ、時刻は個人向けAPIの制約で非対応** | J-Quants個人向けAPI（`/equities/earnings-calendar`） | 必須（J_QUANTS_API_KEY 未設定時、または該当データなしの場合は全件 `status: "needs_review"`） | 実装済み（corporate_events/ に追加、認証方式は未検証、koboriakira/stock-screening#4） |
| `screen` | `--top N` `--test` `--no-cache` | スクリーニング上位N件（スコア内訳付き） | JPX + yfinance | 不要 | 既存 CLI に `--format json` を追加 |
| `evaluate <ticker>` | `--input <csv>` も許容 | Gate1/2/3 判定と各チェック結果 | yfinance（+EDINET） | 任意（EDINET_API_KEY があれば精度向上） | 既存 CLI に `--format json` を追加 |

複数銘柄の一括取得（`quote 7203.T 6758.T ...`）は全コマンド共通で対応する（items が銘柄数分並ぶ）。

### 3.3 出力契約（adapter 共通規約に準拠）

- **stdout に JSON を1オブジェクト出力する**（現 CLI は JSON を stdout に出さないため、これが最大の実装ギャップ）
- 統一シェイプ（既存 adapter-geekly/offers/rss の `{type, count, items}` 規約に準拠）:

```json
{
  "type": "quote",
  "count": 1,
  "items": [{"ticker": "7203.T", "price": 3120, "change_pct": 1.2, "volume": 12345600}],
  "source": "yfinance",
  "fetched_at": "2026-07-12T09:30:00+09:00",
  "cache_hit": false
}
```

- **0件は正常応答**（`{"count": 0, "items": []}`）。エラーと空を区別する
- **データ欠損は `null`**（既存の「データなし=None」原則を維持）。EDINET キー未設定時のチェック結果は `"NEEDS_REVIEW"` を値として返す（エラーにしない）
- **エラーも stdout の JSON**（呼び出し元が常に stdout を JSON としてパースできる）+ 非0 exit code:

```json
{"type": "error", "error": {"code": "rate_limited", "message": "yfinance 429 after 3 retries"}}
```

- exit code: `0` 成功（0件含む）/ `1` データソースエラー / `2` 引数・入力エラー
- **後方互換の規律**: items へのフィールド追加は可。削除・改名・型変更は breaking change とし、呼び出し元スキル（SKILL.md）の更新とセットで行う

### 3.4 非スコープ（adapter 規約「成果物なし・不可逆アクション禁止」の適用)

以下は情報取得ではなく「状態の記録・通知・判断」であり、adapter-stock の契約から除外し、**機能ごと廃止する**（2026-07-12 ユーザー決定）。

| 機能 | 現実装 | 決定 |
|---|---|---|
| ポートフォリオ記録（record-buy/sell/trailing/extension） | timing + portfolio.json | 廃止 |
| ウォッチリスト永続化・クールダウン管理・watchlist-* コマンド | monitoring + watchlist.json | 廃止（シグナル計算だけを `signals` として存続させる） |
| Slack 通知・monitor・daily-report | monitoring/slack_notifier ほか | 廃止（通知はドメイン側の責務） |
| 売買判断・オーダーシート・timing コマンド | timing | 廃止 |

廃止の注意点:

- 既存のローカルデータ（`~/.local/share/stock-screener/` 配下の portfolio.json・watchlist.json・銘柄分析データ・過去レポート）はコード廃止後も**ファイルとして残る**。本システムからの閲覧手段（show-analysis 等）は失われるため、必要な内容は廃止前に確認・退避する
- cron 登録済みの `scripts/daily-monitoring.sh` があれば解除する（登録有無は実装時に `crontab -l` で確認）

## 4. adapter-stock SKILL.md 仕様（グローバルスキル側、新設）

```yaml
---
name: adapter-stock
description: 日本株の株価・出来高・財務・テクニカルシグナル・スクリーニング情報を構造化 JSON で取得するアダプタ。正典実装は ~/git/stock-screening リポジトリの CLI。
argument-hint: "quote <ticker> | history <ticker> | financials <ticker> | signals <ticker> | universe | trading-day | screen | evaluate <ticker>"
allowed-tools: Bash, Read
---
```

本文セクション構成（既存 adapter 群の共通テンプレートに準拠）:

1. なぜアダプタが必要か（取得実装の分散防止、Yahoo WebFetch の再発明防止）
2. 入力（コマンド一覧 = §3.2 の表）
3. 出力（形式 = §3.3 の契約）
4. 前提条件: リポジトリが `~/git/stock-screening` に存在、`uv` 導入済み、`EDINET_API_KEY` は任意
5. 実行方式: `uv run --project /Users/koboriakira/git/stock-screening stock-screener <cmd>` を Bash で実行。単発取得はメイン直接可、複数銘柄一括や screen（分オーダーの処理時間）はバックグラウンド Agent（`model="haiku"`、機械的取得のため）へ委譲
6. 呼び出し元スキル: market-watch の ripple-analysis / decision-review（移行後）、対話セッション
7. エラーハンドリング表:

| 状況 | 対応 |
|---|---|
| `type: error` + `rate_limited` | CLI 内蔵リトライ（指数バックオフ）後の失敗。5分待って1回だけ再実行、それでも失敗なら報告して終了 |
| `count: 0` | 正常応答。「見つからなかった」として扱う（エラーにしない） |
| ticker 不正（exit 2） | 4桁コード + `.T` 形式をユーザーに確認 |
| EDINET チェックが `NEEDS_REVIEW` | 正常応答。キー未設定の旨を添えて報告 |
| リポジトリ不在・uv 失敗 | 処理中断、セットアップ状況を報告（自動修復しない） |

8. 不可逆アクションの禁止: `record-*` 系コマンドを adapter-stock 経由で呼ばない。売買判断・通知はドメイン側の責務

## 5. 非機能要件

- **キャッシュ**: 既存 FileCache（`~/.cache/stock-screener/`、24h TTL）を維持。`--no-cache` で強制再取得。quote/history は鮮度が命なのでキャッシュ対象外（または短TTL を別途設計）
- **レートリミット耐性**: 既存 `retry_on_rate_limit()`（429/接続エラーで指数バックオフ、max 2〜3回）を全取得経路に適用済み。維持する
- **認証**: デフォルト無キーで全コマンドが動作する（EDINET のみオプトイン）。認証情報を stdout に出さない
- **応答時間の目安**: quote/financials/signals は単銘柄数秒、universe は数十秒、screen は分オーダー。SKILL.md に明記し、呼び出し元の委譲判断（メイン直接 or バックグラウンド）の材料にする
- **テスト**: 既存 55 テストファイルの体制を維持し、JSON 出力層には出力シェイプのスナップショットテストを追加（契約の破壊を CI で検出）

## 6. 移行フェーズ案

| Phase | 内容 | 成果物 |
|---|---|---|
| A | 非スコープ機能の廃止: timing・ポートフォリオ記録・ウォッチリスト永続化・Slack 通知・monitor/daily-report のコード・CLI・テストを削除（先行することで以降の実装対象が縮小する） | 本リポジトリのコード |
| B | JSON 出力層の実装: 新コマンド `quote` / `history` / `financials` / `signals` / `universe` / `trading-day`（JSON stdout 既定）+ 既存 `screen` / `evaluate` への `--format json` 追加 + エラー契約 + テスト | 本リポジトリのコード |
| C | adapter-stock SKILL.md 新設 + 本リポジトリ CLAUDE.md / README の位置づけ書き換え | グローバルスキル + ドキュメント |
| D | market-watch の ripple-analysis / decision-review の Yahoo WebFetch を adapter-stock 呼び出しへ置換（「完全独立型」設計の変更は 2026-07-12 に決定済み。実施時に Issue koboriakira/tasks#40 へ経緯を追記する） | market-watch 側の SKILL.md 修正 |

## 7. 既知の課題（調査で見つかった負債）

- `data/calendar.json` は3銘柄のみの手動メンテ。`trading-day` は pandas_market_calendars 由来なので影響ないが、決算日・配当権利日を契約に含めるならデータソースが必要（現状は含めない）
- EDINETコードリスト（`Edinetcode.zip`）の実データ構造を2026-07-18に確認した: 1行目=タイトル行（ダウンロード実行日・件数、当時11,348件）、2行目=ヘッダ行、3行目以降がデータ。エンコーディングは Shift-JIS（cp932）。証券コード列（`証券コード`、13列目）は5桁ゼロ埋め済みで `EdinetClient.ticker_to_sec_code()` の出力形式と一致するため単純な文字列一致で突合できる。非上場の発行会社は証券コード列が空文字列になる。キャッシュは `FileCache(ttl_hours=168)`（1週間）で運用する
- Slack チャンネル ID がハードコード（`slack_notifier.py`）。非スコープ化に伴い当面放置可
- `tmp:issue/` の旧仕様書2件（watchlist v2 / Layer6 PRD）は実装済み機能の初期設計書。位置づけ転換後に docs/ へ整理 or 削除を判断
- codetour のコード規模記述が陳腐化（Phase C のドキュメント更新に含める）
- main ベースラインに ruff format 未適用のドリフトが16ファイル残存（2026-07-12 実装時に3 worker が独立に確認）。Phase C で独立コミットとして一括 format する
- `earnings-date` の J-Quants認証方式は未検証（単一APIキーをヘッダに渡す最も単純な実装のみ実装、モックテストのみで実データ疎通は未確認）。実キー取得後、リフレッシュトークン方式等への修正が必要になる可能性がある（koboriakira/stock-screening#4）
- `earnings-date` は「該当データなし」と「翌営業日分のみ返す設計上の対象外」を区別せず両方 `needs_review` として返す。過去日・将来複数日の一括バックフィルは非対応で、実装時にAPI仕様の再確認が必要

## 8. 決定事項（2026-07-12 ユーザー回答）

1. **非スコープ機能の扱い**: 廃止する（残置・移管はしない）。§3.4 の注意点（ローカルデータの残置・cron 解除）に従う
2. **market-watch の独立型設計**: adapter-stock 依存へ切り替える。取得ロジックの一元化が本転換の主目的のため
3. **リポジトリ名**: 当面 `stock-screening` のまま。リネーム案は https://github.com/koboriakira/tasks/issues/51 で将来判断する
4. **history のデータソース**: yfinance で統一して開始する。欠損が実測されたら Yahoo chart API 直叩きのフォールバック追加を検討する
