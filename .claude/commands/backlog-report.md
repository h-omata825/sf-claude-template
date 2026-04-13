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
from openpyxl.utils import get_column_letter
import os

FOLDER = r"{作業フォルダパス}"
ISSUE_ID = "{課題ID}"
ISSUE_TITLE = "{件名}"
ISSUE_TYPE = "{バグ / 追加要望 / その他}"
PRIORITY = "{優先度}"
DEADLINE = "{期限}"

os.makedirs(FOLDER, exist_ok=True)
wb = openpyxl.Workbook()

# --- スタイル定義 ---
HDR = PatternFill("solid", fgColor="1F3461")   # 紺（ヘッダー）
SEC = PatternFill("solid", fgColor="2E74B5")   # 青（セクション）
SUB = PatternFill("solid", fgColor="D6E4F0")   # 薄青（サブヘッダー）
WHT = Font(color="FFFFFF", bold=True)
BLD = Font(bold=True)
def hdr(ws, row, col, val, fill=HDR, font=WHT):
    c = ws.cell(row=row, column=col, value=val)
    c.fill = fill; c.font = font
    c.alignment = Alignment(wrap_text=True, vertical="center")
    return c

# === Sheet1: サマリー・経緯 ===
ws1 = wb.active; ws1.title = "サマリー・経緯"
ws1.column_dimensions["A"].width = 22
ws1.column_dimensions["B"].width = 50

info = [
    ("課題ID", ISSUE_ID), ("件名", ISSUE_TITLE),
    ("優先度・期限", f"{PRIORITY} / {DEADLINE}"),
    ("課題種別", ISSUE_TYPE), ("ステータス", "対応中"),
    ("対応開始日", ""), ("対応完了日", ""),
    ("担当者", ""), ("見積工数（CC使用）", ""),
    ("見積工数（CC未使用）", ""), ("実績工数（CC使用）", ""),
    ("削減効果", ""), ("", ""),
    ("■ 課題概要", ""), ("", ""),
    ("■ 経緯・背景", ""), ("", ""),
    ("■ ゴール（期待する動作）", ""),
]
for i, (k, v) in enumerate(info, 1):
    ws1.cell(row=i, column=1, value=k).font = BLD
    ws1.cell(row=i, column=2, value=v)

# === Sheet2: 対応方針 ===
ws2 = wb.create_sheet("対応方針")
ws2.column_dimensions["A"].width = 8
for col, w in zip("BCDEFG", [20, 40, 30, 30, 20, 12]):
    ws2.column_dimensions[col].width = w
headers = ["案No", "方針名", "概要", "メリット", "デメリット", "リスク", "工数（CC使用）"]
for i, h in enumerate(headers, 1):
    hdr(ws2, 1, i, h)
ws2.cell(row=3, column=1, value="A★").font = BLD
ws2.cell(row=5, column=1, value="B").font = BLD
for r in [2, 4, 6]:
    ws2.cell(row=r, column=1, value="（根拠）")

# === Sheet3: 調査・影響範囲 ===
ws3 = wb.create_sheet("調査・影響範囲")
for col, w in zip("ABCDE", [6, 30, 30, 40, 10]):
    ws3.column_dimensions[col].width = w
headers3 = ["No", "種別 / 仮説内容", "検証方法", "検証結果・根拠", "判定"]
for i, h in enumerate(headers3, 1):
    hdr(ws3, 1, i, h)

# === Sheet4: 対応内容 ===
ws4 = wb.create_sheet("対応内容")
ws4.column_dimensions["A"].width = 25
ws4.column_dimensions["B"].width = 60
items4 = [
    "Git hash（修正前）", "stash名（バックアップ）",
    "巻き戻し方法", "", "■ 実装手順", "", "", "", "", ""
]
for i, v in enumerate(items4, 1):
    ws4.cell(row=i, column=1, value=v).font = BLD if v.startswith("■") else Font()

# === Sheet5: テスト・検証記録 ===
ws5 = wb.create_sheet("テスト・検証記録")
for col, w in zip("ABCDEFGH", [6, 15, 30, 30, 30, 30, 10, 30]):
    ws5.column_dimensions[col].width = w
headers5 = ["No", "区分", "テスト項目", "確認方法", "期待結果", "実際の結果", "判定", "根拠"]
for i, h in enumerate(headers5, 1):
    hdr(ws5, 1, i, h)

# === Sheet6: リリース・ロールバック ===
ws6 = wb.create_sheet("リリース・ロールバック")
for col, w in zip("ABCDEF", [6, 20, 30, 20, 30, 30]):
    ws6.column_dimensions[col].width = w
headers6 = ["No", "種別", "API名 / 対象", "変更種別", "デプロイ方法", "備考"]
for i, h in enumerate(headers6, 1):
    hdr(ws6, 1, i, h)

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
WHT = Font(color="FFFFFF", bold=True)
BLD = Font(bold=True)

# === Sheet1: テスト仕様 ===
ws1 = wb.active; ws1.title = "テスト仕様"
for col, w in zip("ABCDEFG", [6, 30, 15, 40, 40, 30, 15]):
    ws1.column_dimensions[col].width = w
headers = ["No", "確認観点", "タイミング", "確認手順", "期待結果", "エビデンスの取り方", "貼付先シート"]
for i, h in enumerate(headers, 1):
    c = ws1.cell(row=1, column=i, value=h)
    c.fill = HDR; c.font = WHT

# === Sheet2: 実装前エビデンス ===
ws2 = wb.create_sheet("実装前エビデンス")
for col, w in zip("ABCD", [5, 40, 20, 40]):
    ws2.column_dimensions[col].width = w
for i, h in enumerate(["□", "確認観点", "結果", "メモ（スクリーンショット貼付欄）"], 1):
    c = ws2.cell(row=1, column=i, value=h)
    c.fill = HDR; c.font = WHT
ws2.row_dimensions[1].height = 20

# === Sheet3: 実装後エビデンス ===
ws3 = wb.create_sheet("実装後エビデンス")
for col, w in zip("ABCD", [5, 40, 20, 40]):
    ws3.column_dimensions[col].width = w
for i, h in enumerate(["□", "確認観点", "結果", "メモ（スクリーンショット貼付欄）"], 1):
    c = ws3.cell(row=1, column=i, value=h)
    c.fill = HDR; c.font = WHT
ws3.row_dimensions[1].height = 20

path = os.path.join(FOLDER, f"{ISSUE_ID}_エビデンス.xlsx")
wb.save(path)
print(f"生成完了: {path}")
```

生成完了後、ユーザに報告する:
```
✅ xlsx 生成完了
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

**調査結果を `{課題ID}_対応記録.xlsx` の「調査・影響範囲」シートに記録する（Python で更新）。**

---

## Step 4. 実装前エビデンスの取得（Playwright）

> **実装前の状態を記録する。このStepを飛ばして実装に進むことは禁止。**

1. テスト仕様を検討し、`エビデンス.xlsx` の「テスト仕様」シートに記録する
2. Playwright で対象画面を開く
3. 確認すべき画面・操作ごとにスクリーンショットを撮影する:
   ```
   保存先: {作業フォルダパス}\before_{連番}_{説明}.png
   ```
4. 撮影したスクリーンショットのパスと確認観点を「実装前エビデンス」シートに記録する（openpyxl で画像を挿入する）

> **次に進む条件: 実装前SSの撮影完了・xlsx更新完了後**

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

**`{課題ID}_対応記録.xlsx` の「対応方針」シートに記録する。**

工数見積もりを提示する（`/backlog` Phase 3.7 と同形式）:
- CC使用 見込みXh / CC未使用 見込みXh / 効率化効果 約X倍

**`docs/effort-log.md` に見込みを追記する。**

> **次に進む条件: ユーザが対応方針を承認した後。承認なしに実装に進むことは絶対禁止。**

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

**実装完了後、`{課題ID}_対応記録.xlsx` の「対応内容」シートを更新する（Git hash・変更ファイル・手順を記録）。**

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

テスト結果を `{課題ID}_対応記録.xlsx` の「テスト・検証記録」シートに記録する。

> **次に進む条件: 全テスト項目 ✅ OK になった後。NG があれば Step 7 に戻る。**

---

## Step 9. 実装後エビデンスの取得（Playwright）

> **このStepを飛ばしてデプロイに進むことは禁止。**

1. Step 4 で定義したテスト仕様に従い、実装後の画面を撮影する
2. スクリーンショットを保存する:
   ```
   保存先: {作業フォルダパス}\after_{連番}_{説明}.png
   ```
3. `エビデンス.xlsx` の「実装後エビデンス」シートに画像を挿入する（openpyxl）

ユーザにエビデンス確認を促す:
```
✅ 実装後エビデンスを取得しました。
エビデンスファイルをご確認ください: {作業フォルダパス}\{課題ID}_エビデンス.xlsx
追加で取得が必要なスクリーンショットがあれば指示してください。
```

> **次に進む条件: ユーザがエビデンスを確認した後**

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

**`{課題ID}_対応記録.xlsx` の「リリース・ロールバック」シートを更新する。**

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

⏱ 経過時間
  開始: {Step 0 の時刻}
  終了: {現在時刻}
  経過: {X時間Y分}

途中でブレーク（昼食・休憩等）を挟んだ場合、その時間を教えてください。
例: 「昼食1時間」「休憩30分×2」など。
入力がなければ経過時間がそのまま実績工数になります。
```

実績工数を計算する（経過時間 - ブレーク時間）。

### effort-log.md を更新する

`docs/effort-log.md` の該当行に実績工数と削減効果を記録する。

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
- {課題ID}_エビデンス.xlsx（実装前後SS挿入済み）

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
- Step 2（xlsx作成）と Step 4（実装前SS）は実装（Step 7）より前に必ず完了させる
- Step 5 のユーザ承認なしに実装に進むことは禁止
- Step 9（実装後SS）はデプロイ（Step 10）より前に必ず完了させる
- 本番デプロイは必ずユーザの明示的な指示が必要
