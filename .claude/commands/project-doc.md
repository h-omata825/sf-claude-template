Salesforceプロジェクト資料を会話形式で作成します。
スクリプトは `c:\ClaudeCode\scripts\python\sf-doc-mcp\` にあります。
ソース情報はカレントディレクトリの `docs/` フォルダおよび Salesforce 組織から取得します。

**選択肢は必ず AskUserQuestion ツールで提示する（クリック選択）。テキスト入力は名前・パス等の自由記述のみ。**

---

## Step 0: 資料種別の選択

AskUserQuestion で作成する資料を選択:
- label: "概要書"、description: "プロジェクト概要書 & 業務フロー図 → PPTX"
- label: "オブジェクト定義書"、description: "オブジェクト・項目定義書 → Excel"
- label: "機能別設計書"、description: "機能一覧 & 機能別設計書 → Excel（force-app/ + docs/ から自動生成）"

選択結果によって以下のステップへ分岐する:
- **概要書**           → Step A0（概要書サブメニュー）へ
- **オブジェクト定義書** → Step 1（既存フロー）へ
- **機能別設計書**     → Step C（下記）へ

---

## Step A0: 概要書 — サブメニュー

AskUserQuestion でどちらを作成するか選択:
- label: "プロジェクト概要書"、description: "org-profile.md + requirements.md → PPTX"
- label: "業務フロー図"、description: "swimlanes.json または requirements.md → PPTX"

- **プロジェクト概要書** → Step A（下記）へ
- **業務フロー図**        → Step B（下記）へ

---

## Step A: プロジェクト概要書の生成

### A-1: docs/ フォルダの確認

カレントディレクトリに `docs/` フォルダが存在するか確認:
```bash
python -c "
import pathlib
docs = pathlib.Path('docs')
profile = docs / 'overview' / 'org-profile.md'
req     = docs / 'requirements' / 'requirements.md'
print('profile:', profile.exists())
print('req:', req.exists())
"
```

両ファイルが存在しない場合:「`docs/overview/org-profile.md` が見つかりません。先に `/sf-memory` を実行してください。」と伝えて終了。

### A-2: 作成者名

テキストで聞く:
```
作成者名を入力してください（表紙に表示されます）:
```

### A-3: 出力フォルダ

テキストで聞く:
```
出力先フォルダパスを入力してください:
```

### A-4: 生成

AskUserQuestion で確認後、Bash で実行:
```bash
python c:\ClaudeCode\scripts\python\sf-doc-mcp\generate_project_overview.py \
  --docs-dir "{カレントディレクトリ}/docs" \
  --output-dir "{出力フォルダ}" \
  --author "{作成者名}"
```

完了後、出力パスを表示して終了。

---

## Step B: 業務フロー図の生成

### B-1: ソース確認

カレントディレクトリで以下を確認:
```bash
python -c "
import pathlib
docs = pathlib.Path('docs')
sw   = docs / 'flow' / 'swimlanes.json'
req  = docs / 'requirements' / 'requirements.md'
print('swimlanes:', sw.exists())
print('req:', req.exists())
"
```

- `swimlanes.json` が存在 → 「スイムレーン定義ファイルを使用します（高品質モード）」と表示
- 存在しない・`requirements.md` のみ → 「requirements.md の Mermaid 図から生成します（標準モード）」と表示

### B-2: 作成者名・出力フォルダ

Step A-2 / A-3 と同様に取得する。

### B-3: 生成

AskUserQuestion で確認後、Bash で実行:
```bash
python c:\ClaudeCode\scripts\python\sf-doc-mcp\generate_flow.py \
  --docs-dir "{カレントディレクトリ}/docs" \
  --output-dir "{出力フォルダ}" \
  --author "{作成者名}"
```

完了後、出力パスを表示して終了。

> **新規プロジェクトで swimlanes.json を作成する場合:**
> `docs/flow/swimlanes.json` に以下の形式でフロー定義を保存すると次回から高品質モードで生成できる:
> ```json
> { "flows": [{ "title": "フロー名", "elements": { "lanes": [...], "steps": [...], "arrows": [...] } }] }
> ```
> lanes/steps/arrows の定義はプロジェクトの業務フローに合わせて記述する。

---

## Step 1: 接続先の選択

まずカレントディレクトリの `.sf/config.json` から target-org を取得する:
```bash
python -c "
import json, pathlib, sys
p = pathlib.Path('.sf/config.json')
if p.exists():
    d = json.loads(p.read_text(encoding='utf-8'))
    print(d.get('target-org', ''))
"
```

**target-org が取得できた場合:**
その1件だけを AskUserQuestion で提示（その他で手動入力も可能）:
- label: "{alias}（このプロジェクトのデフォルト組織）" description: ".sf/config.json で設定されている組織"
- label: "その他" description: "別の組織のエイリアスを手動入力"

**target-org が取得できなかった場合:**
「このフォルダにはSalesforce組織が設定されていません。ブラウザでログインします」と伝え、以下を実行:
```bash
sf org login web --alias _doc-tmp
```
ブラウザが開くのでログインしてもらう。完了後 `SF_ALIAS=_doc-tmp` として控える。
（生成完了後に `sf org logout --target-org _doc-tmp --no-prompt` で一時エイリアスを削除する）

---

## Step 2: 作成者名

テキストで聞く:
```
作成者名を入力してください（改版履歴・表紙に表示されます）:
```

---

## Step 3: 出力フォルダ

テキストで聞く:
```
定義書の出力先フォルダパスを入力してください:
```

---

## Step 4: 新規 or 更新の自動判定

Glob でフォルダ内の `オブジェクト項目定義書_v*.xlsx` を確認する。

**既存ファイルがある場合:**
ファイル名を表示したあと、AskUserQuestion でバージョン種別を選択:
- label: "マイナー更新（vX.Y → vX.Y+1）"、description: "変更箇所を赤字表示"
- label: "メジャー更新（vX.Y → vX+1.0）"、description: "赤字をリセットして黒字化"

**既存ファイルがない場合:**
「新規作成モード（v1.0）で進めます」と表示してStep 5へ。

---

## Step 5: システム名称

**新規作成の場合のみ** AskUserQuestion で聞く:
- label: "スキップ" description: "システム名称なしで作成"
- label: "入力する" description: "システム名称を指定する"（Otherで自由入力）

「入力する」または Other が選ばれた場合はテキストで入力してもらう。
更新の場合はこのステップをスキップ（前回の値を自動引き継ぎ）。

---

## Step 6: 対象オブジェクトの選択

**新規作成の場合:**
テキストで入力してもらう:
```
対象オブジェクトを入力してください（API名またはラベル名、複数可）:
（例: Account 取引先責任者 Opportunity__c）
```

**更新の場合:**
まず既存ファイルから前回のオブジェクト一覧を取得する:
```bash
python -c "
import sys
sys.path.insert(0, r'c:\ClaudeCode\scripts\python\sf-doc-mcp')
from meta_store import read_meta
m = read_meta(r'{既存ファイルのフルパス}')
if m:
    print(' '.join(m.get('objects', {}).keys()))
"
```

取得した一覧（例: `Account Opportunity Contact Knowledge__kav`）を表示したうえで、AskUserQuestion で選択:
- label: "既存と同じ（{オブジェクト一覧}）" description: "前回と同じオブジェクトで再生成"
- label: "既存＋追加" description: "既存オブジェクトに追加して生成"
- label: "全て指定し直す" description: "1から対象を指定する"

**「既存と同じ」選択時:** 前回のオブジェクトリストをそのまま使う。
**「既存＋追加」選択時:** テキストで追加オブジェクトを入力してもらい、既存リストに結合する。
**「全て指定し直す」選択時:** テキストで全オブジェクトを入力してもらう。

区切り文字は何でもOK（スペース・カンマ・全角スペース等）。
入力内容を `--objects` に渡す（generate.py 内で名前解決する）。

**スペルチェック:** オブジェクト名に明らかなタイポ（例: Oppotunity → Opportunity）があれば、生成前に確認を取る。

---

## Step 7: 確認して生成

設定内容を表示し、AskUserQuestion で確認:
- label: "生成する"、description: "定義書の生成を開始する"
- label: "キャンセル"、description: "中止する"

「生成する」が選ばれたら Bash で実行:

**SF CLI エイリアスで接続する場合（target-org あり）:**
```bash
python c:\ClaudeCode\scripts\python\sf-doc-mcp\generate.py \
  --sf-alias {SF_ALIAS} \
  --objects {オブジェクトリスト} \
  --output-dir "{出力フォルダ}" \
  --author "{作成者名}" \
  --system-name "{システム名称}" \
  --source-file "{既存ファイルのフルパス（新規は省略）}" \
  --version-increment {minor または major}
```

**username/password で接続する場合（target-org なし）:**
```bash
python c:\ClaudeCode\scripts\python\sf-doc-mcp\generate.py \
  --username {SF_USERNAME} \
  --password {SF_PASSWORD} \
  --security-token {SF_TOKEN} \
  --domain {login または test} \
  --objects {オブジェクトリスト} \
  --output-dir "{出力フォルダ}" \
  --author "{作成者名}" \
  --system-name "{システム名称}" \
  --source-file "{既存ファイルのフルパス（新規は省略）}" \
  --version-increment {minor または major}
```

---

## Step 8: 完了案内

出力パスを表示する。

ブラウザログインを使った場合（SF_ALIAS=_doc-tmp）は後処理として実行:
```bash
sf org logout --target-org _doc-tmp --no-prompt
```

内容について質問があれば対応する。

---

## Step C: 機能別設計書

### C-1: 共通情報の取得

テキストで聞く:
```
出力先フォルダパスを入力してください:
作成者名を入力してください:
プロジェクト名を入力してください（Excelの表紙に表示されます）:
```

### C-2: force-app/ をスキャンして機能一覧を取得

```bash
python c:\ClaudeCode\scripts\python\sf-doc-mcp\scan_features.py \
  --project-dir "{カレントディレクトリ}"
```

スキャン結果を表示し、AskUserQuestion で確認:
- label: "全機能を生成する"、description: "スキャンで検出された全機能の設計書を生成"
- label: "特定の機能を選択する"、description: "次のメッセージで機能IDまたは名前を入力"

「特定の機能を選択する」の場合はテキストで入力してもらい、対象を絞り込む。

### C-3: 各機能のソースを読んで設計内容を生成

対象機能ごとに以下を実施する（全機能が多い場合は並列で処理）:

1. **ソースファイルを読む**
   - `force-app/` の該当クラス/フロー/コンポーネントを Read
   - `docs/design/` に対応するMDがあれば Read
   - 情報が足りない場合は Salesforce CLI で組織から補完:
     ```bash
     sf apex get class --class-name {ClassName} --target-org {SF_ALIAS}
     ```

2. **設計内容をJSON形式で整理する**（下記フォーマット）

```json
{
  "id": "F-001",
  "type": "Apex",
  "name": "機能名（日本語）",
  "api_name": "ClassName",
  "project_name": "{プロジェクト名}",
  "system_name": "",
  "author": "{作成者名}",
  "version": "1.0",
  "date": "YYYY-MM-DD",
  "purpose": "本書の目的",
  "overview": "処理概要",
  "prerequisites": "前提条件（なければ「特になし」）",
  "trigger": "処理契機",
  "steps": [
    { "no": "1", "title": "ステップタイトル", "detail": "詳細",
      "sub_steps": [{ "no": "1.1", "title": "サブタイトル", "detail": "詳細" }] }
  ],
  "input_params":  [{ "key": "param1", "type": "String",  "required": true,  "description": "説明" }],
  "output_params": [{ "key": "result", "type": "Boolean", "description": "説明" }]
}
```

3. **JSONを一時ファイルに保存**
   - 保存先: `{出力フォルダ}/.tmp/{api_name}_design.json`

4. **LWC / 画面フローの場合: スクリーンショット取得（可能であれば）**
   - Playwright が使用可能な場合、対象コンポーネントが表示されているページを撮影
   - 保存先: `{出力フォルダ}/.tmp/{api_name}_screen.png`
   - 取得できない場合はスキップ（設計書の「画面イメージ」セクションを省略）

### C-4: 機能設計書.xlsx を生成

各機能について Python スクリプトを実行:

```bash
python c:\ClaudeCode\scripts\python\sf-doc-mcp\generate_feature_design.py \
  --input "{出力フォルダ}/.tmp/{api_name}_design.json" \
  --output-dir "{出力フォルダ}" \
  [--screenshot "{出力フォルダ}/.tmp/{api_name}_screen.png"]
```

出力ファイル名: `機能設計書_{機能ID}_{api_name}.xlsx`

### C-5: 機能一覧.xlsx を生成

全機能の JSON から機能一覧用の要約 JSON を作成し実行:

```bash
python c:\ClaudeCode\scripts\python\sf-doc-mcp\generate_feature_list.py \
  --input "{出力フォルダ}/.tmp/feature_list.json" \
  --output-dir "{出力フォルダ}" \
  --author "{作成者名}" \
  --project-name "{プロジェクト名}"
```

`feature_list.json` の形式:
```json
[
  {
    "id": "F-001",
    "type": "Apex",
    "name": "機能名",
    "api_name": "ClassName",
    "overview": "処理概要（1〜2文）",
    "design_file": "機能設計書_F-001_ClassName.xlsx"
  }
]
```

### C-6: 後処理・完了報告

```bash
# 一時ファイルを削除
rm -rf "{出力フォルダ}/.tmp"
```

完了報告:
```
✅ 機能一覧.xlsx — 1ファイル（{機能数}件）
✅ 機能設計書.xlsx — {機能数}ファイル
出力先: {出力フォルダ}
```
