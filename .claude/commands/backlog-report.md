# /backlog-report [課題ID] または [summary]

保守課題の対応を、xlsx記録の作成 → 実装 → エビデンス取得まで一気通貫で実施する。

**`/backlog-report [課題ID]`** — 対応記録・エビデンスxlsxを作成しながら作業を完遂する（メインワークフロー）
**`/backlog-report summary`** — `docs/effort-log.md` の工数サマリーを出力する

---

## 引数

- `[課題ID]` — Backlog の課題ID（例: `GF-327`）
- `summary` — 全課題の工数サマリーを出力して終了

---

## [summary] モードの動作

`docs/effort-log.md` を読み込み、以下の形式でサマリーを出力する:

```
## 工数サマリー

### 全課題一覧
| 課題ID | 件名 | 種別 | 見込み（CC） | 見込み（非CC） | 実績（CC） | 削減効果 | 対応日 |

### 集計（実績記録済みのみ）
- 対応課題数 / CC使用合計 / CC未使用見込み合計 / 削減時間合計 / 平均削減率 / 見込み精度

### 種別内訳（バグ / 追加要望 / その他）
```

---

## [課題ID] モードの動作

以降は `[課題ID]` を指定した場合の完全ワークフロー。

> **【絶対ルール】**
> - 各Stepは必ず順番通りに実行する。前のStepが完了するまで次に進まない
> - Stepを飛ばすこと・並行して進めることは禁止
> - 実装は Step 7 以降。それ以前に実装コードを書くことは禁止

---

## xlsx 逐次更新ルール

対応記録.xlsx は**各 Step の完了時に必ず更新する**。以下のタイミングで何を記録するかを厳守する。

| Step | 更新対象シート | 記録内容 |
|---|---|---|
| Step 1 | サマリー・経緯 | 課題サマリー欄 + タイムラインに「課題取得」行を追加 |
| Step 3 | 調査・影響範囲 | 仮説検証テーブルに調査結果を記録 |
| Step 4 | （エビデンス.xlsx） | テスト仕様シート + 実装前エビデンスシート |
| Step 5 | 対応方針 | 方針比較テーブル + 採用方針を記録。サマリーのタイムラインに追記 |
| Step 7 | 対応内容 | Git hash・変更ファイル一覧・Before/After・影響確認チェックリスト |
| Step 8 | テスト・検証記録 | テスト結果を全行記録 |
| Step 9 | （エビデンス.xlsx） | 実装後エビデンスシート |
| Step 10 | リリース・ロールバック | リリース対象一覧・ロールバック手順 |
| Step 12 | サマリー・経緯 | 完了時刻・実績工数・最終対応サマリー |

**ユーザとのやりとり・方針変更・追加修正が発生するたびに、サマリー・経緯の「対応経緯タイムライン」に行を追加する。**
タイムラインの記録は Step 全体を通じて継続的に行う（特定の Step に限定しない）。

---

## Step 0. 開始時刻を記録する

現在時刻を取得して変数として保持する:

```bash
date "+%Y-%m-%d %H:%M:%S"
```

**この時刻を会話の最後まで保持する。セッション内で参照できるようにする。**

---

## Step 1. 課題取得と内容確認

Backlog MCP で課題を取得する:
- 件名・説明・優先度・期限・ステータス
- カテゴリ・マイルストーン
- コメント（全件）

取得後、課題内容を自分の言葉で要約してユーザに提示し、理解が正しいか確認する。

> **次に進む条件: ユーザが「OK」「合ってる」等の確認をした後**

---

## Step 2. 作業フォルダと xlsx の作成

> **このStepは実装より前に必ず実行する。xlsx を作らずに Step 7 以降に進むことは禁止。**

### 2-1. フォルダパスの確定

保存先フォルダを確認する（GF プロジェクトのデフォルト: `C:\work\01_作業\グリーンフィールド\保守課題\`）。
プロジェクトのCLAUDE.mdに `BACKLOG_REPORT_DIR` が定義されていればそれを使用する。

フォルダパスをユーザに提示して確認を取る:
```
作業フォルダ: C:\work\01_作業\グリーンフィールド\保守課題\{課題ID}_{件名}\
このフォルダに対応記録.xlsx と エビデンス.xlsx を作成します。よろしいですか？
```

> **次に進む条件: ユーザが確認した後**

### 2-2. 対応記録.xlsx の生成

以下の Python スクリプトを実行して `{課題ID}_対応記録.xlsx` を生成する:

```python
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
import os

FOLDER = r"{作業フォルダパス}"
ISSUE_ID = "{課題ID}"
ISSUE_TITLE = "{件名}"
ISSUE_TYPE = "{バグ / 追加要望 / その他}"
PRIORITY = "{優先度}"
DEADLINE = "{期限}"
BG_DESC = "{背景・要件の要約}"

os.makedirs(FOLDER, exist_ok=True)
wb = openpyxl.Workbook()

# --- スタイル定義 ---
HDR = PatternFill("solid", fgColor="1F3461")   # 紺（ヘッダー）
SEC = PatternFill("solid", fgColor="2E74B5")   # 青（セクション）
SUB = PatternFill("solid", fgColor="D6E4F0")   # 薄青（サブヘッダー）
WHT = Font(color="FFFFFF", bold=True)
BLD = Font(bold=True)
WRAP = Alignment(wrap_text=True, vertical="top")

def sec_header(ws, row, col, val):
    """■ セクション見出し（青背景白文字）"""
    c = ws.cell(row=row, column=col, value=val)
    c.fill = SEC; c.font = WHT; c.alignment = WRAP
    return c

def col_header(ws, row, col, val):
    """列ヘッダー（紺背景白文字）"""
    c = ws.cell(row=row, column=col, value=val)
    c.fill = HDR; c.font = WHT; c.alignment = WRAP
    return c

def bold_cell(ws, row, col, val):
    c = ws.cell(row=row, column=col, value=val)
    c.font = BLD; c.alignment = WRAP
    return c

# ==========================================================
# Sheet1: サマリー・経緯
# ==========================================================
ws1 = wb.active; ws1.title = "サマリー・経緯"
ws1.column_dimensions["A"].width = 22
ws1.column_dimensions["B"].width = 60
ws1.column_dimensions["C"].width = 12
ws1.column_dimensions["D"].width = 18
ws1.column_dimensions["E"].width = 60
ws1.column_dimensions["F"].width = 40

sec_header(ws1, 1, 1, "サマリー・経緯")

# ■ 課題サマリー
sec_header(ws1, 2, 1, "■ 課題サマリー")
info = [
    ("課題ID", ISSUE_ID),
    ("件名", ISSUE_TITLE),
    ("優先度・期限", f"優先度: {PRIORITY} / 期限: {DEADLINE}"),
    ("課題種別", ISSUE_TYPE),
    ("ステータス", "対応中"),
    ("背景・要件", BG_DESC),
    ("最終対応サマリー", "（完了時に記入）"),
]
r = 3
for k, v in info:
    bold_cell(ws1, r, 1, k)
    ws1.cell(row=r, column=2, value=v).alignment = WRAP
    r += 1

# ■ 工数（サマリー内に工数セクション）
r += 1
sec_header(ws1, r, 1, "■ 工数")
r += 1
for k in ["対応開始日時", "対応完了日時", "見積工数（CC使用）", "見積工数（CC未使用）", "実績工数（CC使用）", "削減効果"]:
    bold_cell(ws1, r, 1, k)
    r += 1

# ■ 対応経緯タイムライン
r += 1
sec_header(ws1, r, 1, "■ 対応経緯タイムライン")
r += 1
for i, h in enumerate(["No", "日時", "発生元", "フェーズ", "内容・決定事項", "変更・判断の理由"], 1):
    col_header(ws1, r, i, h)
TIMELINE_HEADER_ROW = r  # この行番号を覚えておく（後続Step で追記する起点）

# ==========================================================
# Sheet2: 対応方針
# ==========================================================
ws2 = wb.create_sheet("対応方針")
ws2.column_dimensions["A"].width = 10
for col, w in zip("BCDEFG", [22, 45, 32, 32, 22, 14]):
    ws2.column_dimensions[col].width = w

sec_header(ws2, 1, 1, "対応方針")

# ■ 方針比較テーブル
sec_header(ws2, 2, 1, "■ 方針比較テーブル")
for i, h in enumerate(["案No", "方針名", "概要", "メリット", "デメリット", "リスク", "工数"], 1):
    col_header(ws2, 3, i, h)
# 案A（推奨）
bold_cell(ws2, 4, 1, "A★")
ws2.cell(row=5, column=1, value="（根拠）").alignment = WRAP
# 案B
bold_cell(ws2, 6, 1, "B")
ws2.cell(row=7, column=1, value="（根拠）").alignment = WRAP

# ■ 採用方針（方針確定後に記入）
sec_header(ws2, 9, 1, "■ 採用方針")
ws2.cell(row=10, column=1, value="（方針確定後にここに採用理由を記録する）").alignment = WRAP

# ■ 構成比較・差分記録（必要に応じて使用）
sec_header(ws2, 12, 1, "■ 構成比較・差分記録（必要に応じて）")
for i, h in enumerate(["要素", "既存（比較元）", "今回（実装対象）", "差分"], 1):
    col_header(ws2, 13, i, h)

# ==========================================================
# Sheet3: 調査・影響範囲
# ==========================================================
ws3 = wb.create_sheet("調査・影響範囲")
for col, w in zip("ABCDE", [6, 35, 35, 45, 10]):
    ws3.column_dimensions[col].width = w

sec_header(ws3, 1, 1, "調査・影響範囲")
sec_header(ws3, 2, 1, "■ 仮説検証テーブル")
for i, h in enumerate(["No", "仮説内容 / 種別", "検証方法", "検証結果・根拠", "判定"], 1):
    col_header(ws3, 3, i, h)

# ==========================================================
# Sheet4: 対応内容
# ==========================================================
ws4 = wb.create_sheet("対応内容")
ws4.column_dimensions["A"].width = 28
ws4.column_dimensions["B"].width = 55
ws4.column_dimensions["C"].width = 15
ws4.column_dimensions["D"].width = 50
ws4.column_dimensions["E"].width = 50

sec_header(ws4, 1, 1, "対応内容")

# ■ バックアップ情報
sec_header(ws4, 2, 1, "■ バックアップ情報（修正前に記録）")
bold_cell(ws4, 3, 1, "Git hash（修正前）")
ws4.cell(row=3, column=2, value="（実装前に記録: git rev-parse HEAD）")
bold_cell(ws4, 4, 1, "stash名")
ws4.cell(row=4, column=2, value="（stash使用時に記録）")
bold_cell(ws4, 5, 1, "巻き戻し方法")
ws4.cell(row=5, column=2, value="git reset --hard [hash] または git stash pop")

# ■ 変更ファイル一覧
sec_header(ws4, 7, 1, "■ 変更ファイル一覧")
for i, h in enumerate(["No", "ファイルパス", "変更種別", "変更概要"], 1):
    col_header(ws4, 8, i, h)

# ■ Before / After
sec_header(ws4, 15, 1, "■ Before / After（実装後に記入）")
ws4.cell(row=16, column=1, value="実装完了後、各ファイルの変更前後を記載する").alignment = WRAP

# ■ 影響確認チェックリスト
sec_header(ws4, 20, 1, "■ 影響確認チェックリスト")
for i, h in enumerate(["□", "確認内容", "結果", "備考"], 1):
    col_header(ws4, 21, i, h)

# ■ 追加修正（修正が複数回発生した場合に使用）
sec_header(ws4, 30, 1, "■ 追加修正（必要に応じて追記）")
for i, h in enumerate(["No", "ファイルパス", "変更種別", "変更概要", "詳細・根拠"], 1):
    col_header(ws4, 31, i, h)

# ==========================================================
# Sheet5: テスト・検証記録
# ==========================================================
ws5 = wb.create_sheet("テスト・検証記録")
for col, w in zip("ABCDEFGH", [6, 16, 32, 32, 32, 32, 10, 35]):
    ws5.column_dimensions[col].width = w

sec_header(ws5, 1, 1, "テスト・検証記録")
sec_header(ws5, 2, 1, "■ テスト方針")
ws5.cell(row=3, column=1, value="（テスト方針・観点をここに記載する）").alignment = WRAP
sec_header(ws5, 5, 1, "■ テスト結果")
for i, h in enumerate(["No", "区分", "テスト項目", "確認方法", "期待結果", "実際の結果", "判定", "根拠"], 1):
    col_header(ws5, 6, i, h)

# ==========================================================
# Sheet6: リリース・ロールバック
# ==========================================================
ws6 = wb.create_sheet("リリース・ロールバック")
for col, w in zip("ABCDEF", [6, 22, 35, 20, 32, 32]):
    ws6.column_dimensions[col].width = w

sec_header(ws6, 1, 1, "リリース・ロールバック")
sec_header(ws6, 2, 1, "■ リリース対象一覧")
for i, h in enumerate(["No", "種別", "API名 / 対象", "変更種別", "デプロイ方法", "備考"], 1):
    col_header(ws6, 3, i, h)

sec_header(ws6, 12, 1, "■ ロールバック手順")
ws6.cell(row=13, column=1, value="（ロールバックが必要な場合の手順を記載する）").alignment = WRAP

sec_header(ws6, 16, 1, "■ 本番デプロイ記録")
for k in ["デプロイ日時", "実施者", "検証結果"]:
    bold_cell(ws6, ws6.max_row + 1, 1, k)

path = os.path.join(FOLDER, f"{ISSUE_ID}_対応記録.xlsx")
wb.save(path)
print(f"生成完了: {path}")
```

### 2-3. エビデンス.xlsx の生成

```python
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment
import os

FOLDER = r"{作業フォルダパス}"
ISSUE_ID = "{課題ID}"

wb = openpyxl.Workbook()

HDR = PatternFill("solid", fgColor="1F3461")
SEC = PatternFill("solid", fgColor="2E74B5")
WHT = Font(color="FFFFFF", bold=True)
WRAP = Alignment(wrap_text=True, vertical="top")

def col_header(ws, row, col, val):
    c = ws.cell(row=row, column=col, value=val)
    c.fill = HDR; c.font = WHT; c.alignment = WRAP

# === Sheet1: テスト仕様 ===
ws1 = wb.active; ws1.title = "テスト仕様"
for col, w in zip("ABCDEFG", [6, 32, 15, 42, 42, 32, 18]):
    ws1.column_dimensions[col].width = w
for i, h in enumerate(["No", "確認観点", "タイミング", "確認手順", "期待結果", "エビデンスの取り方", "貼付先シート"], 1):
    col_header(ws1, 1, i, h)

# === Sheet2: 実装前エビデンス ===
ws2 = wb.create_sheet("実装前エビデンス")
for col, w in zip("ABCD", [5, 42, 20, 50]):
    ws2.column_dimensions[col].width = w
for i, h in enumerate(["□", "確認観点", "結果", "メモ（スクリーンショット貼付欄）"], 1):
    col_header(ws2, 1, i, h)

# === Sheet3: 実装後エビデンス ===
ws3 = wb.create_sheet("実装後エビデンス")
for col, w in zip("ABCD", [5, 42, 20, 50]):
    ws3.column_dimensions[col].width = w
for i, h in enumerate(["□", "確認観点", "結果", "メモ（スクリーンショット貼付欄）"], 1):
    col_header(ws3, 1, i, h)

path = os.path.join(FOLDER, f"{ISSUE_ID}_エビデンス.xlsx")
wb.save(path)
print(f"生成完了: {path}")
```

生成完了後、ユーザに報告する:
```
xlsx 生成完了
- {課題ID}_対応記録.xlsx（6シート）
- {課題ID}_エビデンス.xlsx（3シート）
保存先: {作業フォルダパス}
```

> **次に進む条件: 両ファイルの生成を確認した後**

---

## Step 3. 調査・影響範囲の特定

`/backlog` の Phase 2 相当の調査を実施する。

- `force-app/` および `docs/` を読み込み、関連コンポーネントを特定する
- バグの場合: 原因を多重検証で特定する
- 追加要望の場合: 関連実装を全て読む

**xlsx 更新:**
- `{課題ID}_対応記録.xlsx` の「調査・影響範囲」シートに仮説検証テーブルを記録する
- 「サマリー・経緯」の対応経緯タイムラインに調査の経過を追記する

---

## Step 4. 実装前エビデンスの取得（可能であれば）

> **実装前の状態を記録する。Playwright でスクリーンショットが取得できる場合のみ実施。**
> **精度の低いエビデンスは取得しない。取得できない場合はテスト仕様シートの作成のみ行い Step 5 に進む。**

1. テスト仕様を検討し、`エビデンス.xlsx` の「テスト仕様」シートに記録する（これは必須）
2. 可能であれば Playwright で対象画面を開き、スクリーンショットを撮影する:
   ```
   保存先: {作業フォルダパス}\before_{連番}_{説明}.png
   ```
3. 撮影した場合は「実装前エビデンス」シートに記録する

---

## Step 5. 対応方針の提案とユーザ承認

`/backlog` の Phase 3 相当の内容を提示する:

```
## 課題: [課題ID] [件名]

### 原因 / 要件
[特定した原因または要件の詳細]

### 影響範囲
[直接・間接の影響箇所]

### 対応方針（案）

#### 案A★ [方針名]
- 概要 / メリット / デメリット / リスク / 見込み工数（CC使用）: Xh

#### 案B [方針名]（複数ある場合）

### 推奨案と根拠

### 実施前の確認事項
```

**xlsx 更新:**
- 「対応方針」シートの方針比較テーブルに記録する
- ユーザが承認したら「採用方針」セクションに採用理由を記録する
- 構成比較が必要な場合（既存実装との比較等）は「構成比較・差分記録」に記録する
- 「サマリー・経緯」のタイムラインに方針提案・承認を追記する

工数見積もりを提示する（`/backlog` Phase 3.7 と同形式）:
- CC使用 見込みXh / CC未使用 見込みXh / 効率化効果 約X倍
- 「サマリー・経緯」の工数セクションに見込みを記録する

**`docs/effort-log.md` に見込みを追記する。**

> **次に進む条件: ユーザが対応方針を承認した後。承認なしに実装に進むことは絶対禁止。**

**方針変更が発生した場合:**
- 対応方針シートの採用方針を更新する（旧方針は取り消し線 or 「変更前」として残す）
- タイムラインに変更の経緯・理由を追記する
- 方針変更のたびに xlsx を更新する

---

## Step 6. 方針のクロスレビュー

`/backlog` の Phase 3.5 相当のセルフレビューを実施する:
- 影響範囲の見落としがないか
- 権限・FLS・セキュリティへの影響を確認しているか
- 副作用が洗い出されているか

問題があれば Step 5 の提案内容を修正してから次に進む。

---

## Step 7. 実装

`/backlog` の Phase 5 相当の実装を行う。

- 修正前に対象ファイルを必ず読む
- 修正は最小限にとどめる
- 変更内容を Before / After 形式でユーザに提示する

**xlsx 更新（「対応内容」シート）:**
- Git hash（修正前）を記録する
- 変更ファイル一覧を記録する（No / ファイルパス / 変更種別 / 変更概要）
- Before / After セクションに変更前後を記録する
- 影響確認チェックリストに確認すべき項目を列挙する
- タイムラインに実装完了を追記する

**追加修正が発生した場合:**
- 「追加修正」セクションに追加修正の内容を記録する（追加修正ごとに日付・根拠を明記）
- タイムラインにも追加修正の経緯を追記する

---

## Step 8. テスト・検証

`/backlog` の Phase 6 相当のテストを実施する。

### 8-1. 実装レビュー（reviewer 観点）

- [ ] ガバナ制限 / バルク処理 / エラーハンドリング / ハードコードなし
- [ ] FLS / CRUD / with sharing / ページレイアウト / 権限セット

### 8-2. 機能テスト（Playwright で実施）

- テスト用新規データを作成する（既存の本番・顧客データは使わない）
- 実際にユーザが行う操作フローを通して実行する
- 変更した機能・同画面の既存機能・影響範囲の全てを確認する

### 8-3. Apex テスト（コード変更がある場合）

```bash
sf apex run test --target-org <alias> --class-names <テストクラス名> --result-format human --code-coverage
```

### 8-4. テスト結果を xlsx に記録する

**xlsx 更新（「テスト・検証記録」シート）:**
- テスト方針を記録する
- テスト結果を全行記録する（No / 区分 / テスト項目 / 確認方法 / 期待結果 / 実際の結果 / 判定 / 根拠）
- タイムラインにテスト結果（全OK or NG項目あり）を追記する

**NG 発生時:**
- タイムラインに NG 内容・ユーザ報告・Claude の追加調査を時系列で記録する
- Step 7 に戻って修正し、「追加修正」セクションと「変更ファイル一覧」を更新する
- 修正後は再度 Step 8 を最初からやり直す

> **次に進む条件: 全テスト項目 OK になった後。NG があれば Step 7 に戻る。**

---

## Step 9. 実装後エビデンスの取得（可能であれば）

> **Playwright でスクリーンショットが取得できる場合のみ実施。**
> **精度の低いエビデンスは取得しない。取得できない場合はエビデンス.xlsx のテスト仕様シートが記録済みであれば Step 10 に進む。**

1. Step 4 で定義したテスト仕様に従い、実装後の画面を撮影する
2. スクリーンショットを保存する:
   ```
   保存先: {作業フォルダパス}\after_{連番}_{説明}.png
   ```
3. `エビデンス.xlsx` の「実装後エビデンス」シートに記録する

---

## Step 10. デプロイ

1. デプロイ対象の資材を一覧化する
2. デプロイ検証を実行する:
   ```bash
   sf project deploy start --dry-run --source-dir force-app
   ```
3. ユーザにデプロイ実行の確認を取る
4. デプロイを実行する
5. デプロイ後の動作確認を行う

**xlsx 更新（「リリース・ロールバック」シート）:**
- リリース対象一覧を記録する（No / 種別 / API名 / 変更種別 / デプロイ方法 / 備考）
- ロールバック手順を記録する

本番デプロイはユーザの明示的な指示が必要。

---

## Step 11. ドキュメント更新

- `docs/decisions.md` に判断記録を追記する（対応方針の選定理由・排除した案とその理由）
- 変更したオブジェクト・コード・設定に対応する `docs/` の資料を更新する

---

## Step 12. 工数記録・完了処理

### 終了時刻を取得する

```bash
date "+%Y-%m-%d %H:%M:%S"
```

### ユーザに確認する

```
作業完了しました。

経過時間
  開始: {Step 0 の時刻}
  終了: {現在時刻}
  経過: {X時間Y分}

途中でブレーク（昼食・休憩等）を挟んだ場合、その時間を教えてください。
例: 「昼食1時間」「休憩30分×2」など。
入力がなければ経過時間がそのまま実績工数になります。
```

実績工数を計算する（経過時間 - ブレーク時間）。

### xlsx・effort-log の最終更新

**xlsx 更新（「サマリー・経緯」シート）:**
- 完了日時・実績工数・削減効果を記録する
- ステータスを「完了」に更新する
- 最終対応サマリーを記述する（GF-327 の例: 「handleSaveDraft()を全面実装：BT + Quote の両方保存。getInitData SOQL に5フィールド追加…」）

**`docs/effort-log.md`** の該当行に実績工数と削減効果を記録する。

### サマリーを報告する

```
## {課題ID} 対応完了

### 工数
| 区分 | 工数 |
|---|---|
| 見込み（CC使用） | Xh |
| 見込み（CC未使用） | Xh |
| 実績（CC使用） | Xh |
| 削減効果 | Xh 削減（X%） / 見込み精度 ±X% |

### 成果物
- {課題ID}_対応記録.xlsx（6シート記録済み）
- {課題ID}_エビデンス.xlsx（テスト仕様 + エビデンス）

### 次のアクション
- [ ] 本番デプロイ（要ユーザ指示）
- [ ] お客様への完了報告
```

---

## 使用例

```
/backlog-report GF-327     # GF-327 の対応を記録付きで実施
/backlog-report summary    # 全課題の工数サマリーを出力
```

## 注意

- 各 Step は必ず順番通りに実行する
- Step 2（xlsx作成）は実装（Step 7）より前に必ず完了させる
- Step 5 のユーザ承認なしに実装に進むことは禁止
- 本番デプロイは必ずユーザの明示的な指示が必要
- ユーザとのやりとり・方針変更・追加修正が発生するたびにタイムラインに追記する
- 対応方針が変更されたら対応方針シートも合わせて更新する
