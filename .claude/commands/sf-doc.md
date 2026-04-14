Salesforceプロジェクト資料を会話形式で作成します。
スクリプトは `c:\ClaudeCode\scripts\python\sf-doc-mcp\` にあります。
ソース情報はカレントディレクトリの `docs/` フォルダおよび Salesforce 組織から取得します。

**選択肢は必ず AskUserQuestion ツールで提示する（クリック選択）。テキスト入力は名前・パス等の自由記述のみ。**

---

## Step 0: 資料種別の選択

AskUserQuestion で作成する資料を選択（**上流 → 下流** の順）:

| # | 資料 | 出力 | 分岐 |
|---|---|---|---|
| 0 | 全て                       | 全資料を順番に生成（A→B→C→D）                                  | Step A〜D |
| 1 | 業務フロー図               | PPTX（システム構成図・業務フロー図・ER図・オブジェクト一覧）   | Step A→B |
| 2 | オブジェクト定義書          | Excel（オブジェクト項目定義書）                                 | Step C |
| 3 | 機能別設計書                | Excel（機能一覧＋機能別設計書）                                 | Step D |

AskUserQuestion のツールを使い、以下の **4つ** を choices に含めて提示する:

- 全て — 全資料を順番に生成（A→B→C→D）
- 業務フロー図 — システム構成図・業務フロー図・ER図 → PPTX
- オブジェクト定義書 — オブジェクト・項目定義書 → Excel
- 機能別設計書 — 機能一覧 & 機能別設計書 → Excel

「全て」→ A-1 からそのまま D まで順番に実行する。
「業務フロー図」→ Step A 完了後そのまま Step B を実行する。

### Step 0-2: 共通情報の取得（資料種別選択後に一度だけ聞く）

**管理フォルダ**: テキストメッセージで直接聞く。AskUserQuestion は使わず、選択肢・例も表示しない:
```
資料の管理フォルダパスを入力してください:
```

入力後、サブフォルダ誤指定チェックを実行:
```bash
python -c "
import pathlib, sys
p = pathlib.Path(r'{入力値}')
known = ['業務フロー図', 'オブジェクト定義書', '機能別設計書']
if p.name in known:
    print('PARENT:' + str(p.parent))
else:
    print('OK:' + str(p))
"
```
出力が `PARENT:` で始まる場合: 「サブフォルダが指定されました。親フォルダ {parent} を管理フォルダとして使用します。」と伝え、親パスを `ROOT` として使用する。
出力が `OK:` の場合: そのまま `ROOT` として使用する。

**作成者名**: AskUserQuestion で以下の **2択** のみ提示する:
- label: "スキップ"、description: "作成者名なし"
- label: "Other"（自由入力）

**プロジェクト名**（機能別設計書 / 全て を選択した場合のみ）:
```
プロジェクト名を入力してください（Excelの表紙に表示されます）:
```

> 以降の各Stepでは管理フォルダ・作成者名・プロジェクト名を再度聞かない。

---

## Step A: 業務フロー図・システム構成図（PPTX）

> - 本書の中身は **docs/ 配下の精度に完全依存** する。docs が薄いと骨組みだけのスライドになる。
> - 既存のプロジェクト資料（要件定義書・業務フロー図・システム構成図など）がある場合は、**先に /sf-memory で読み込ませてから**本コマンドを実行すること。
> - 図（システム構成図・業務フロー図）は自動配置のため、位置・重なりに限界がある。手直しを想定すること。

### 生成されるスライド構成

| # | スライド | 必須/条件 | ソース |
|---|---|---|---|
| 1 | 表紙・目次 | 必須 | 自動 |
| 2 | プロジェクト概要 | 必須 | `docs/overview/org-profile.md` + `docs/requirements/requirements.md` |
| 3 | システム構成図 | 必須 | `docs/architecture/system.json` |
| 4 | 業務フロー図（全体） | 必須 | `docs/flow/swimlanes.json`（flow_type: "overall"） |
| 5 | 業務フロー図（UC別） | 必須 | `docs/flow/swimlanes.json`（flow_type: "usecase"、UCごと1枚） |
| 6 | 業務フロー図（例外・承認） | 任意 | `docs/flow/swimlanes.json`（flow_type: "exception"） |
| 7 | データの流れ図 | 任意 | `docs/flow/swimlanes.json`（flow_type: "dataflow"） |

### A-1: docs/ フォルダの確認

カレントディレクトリで以下の存在を確認:

```bash
python -c "
import pathlib
docs = pathlib.Path('docs')
paths = {
    'profile':   docs / 'overview'     / 'org-profile.md',
    'req':       docs / 'requirements' / 'requirements.md',
    'system':    docs / 'architecture' / 'system.json',
    'swimlanes': docs / 'flow'         / 'swimlanes.json',
    'usecases':  docs / 'flow'         / 'usecases.md',
}
for k, p in paths.items():
    print(f'{k}: {p.exists()}')
"
```

- `profile` / `req` が両方ない場合:「先に `/sf-memory` を実行してください。」と伝えて終了。
- `system.json` がない場合: 「システム構成図がスキップされます。/sf-memory でシステム構成情報を追加してください。」と表示して続行。
- `swimlanes.json` がない場合: 「業務フロー図がスキップされます。/sf-memory で業務フロー情報を追加してください。」と表示して続行。

### A-2: 生成

出力先サブフォルダを作成してから実行:
```bash
mkdir -p "{ROOT}/業務フロー図"
python c:\ClaudeCode\scripts\python\sf-doc-mcp\generate_project_doc.py \
  --docs-dir "{カレントディレクトリ}/docs" \
  --output-dir "{ROOT}/業務フロー図" \
  --author "{作成者名}"
```

完了後、出力パスを表示:
- `{ROOT}/業務フロー図/業務フロー図.pptx`

---

## Step B: データモデル定義書

> - オブジェクト・項目・リレーション等の**事実情報はメタデータから正確に取得できる**。一方で「なぜこの項目が必要か」「オブジェクトの業務的意味」「論理ER図」は**メタデータから復元不可**。
> - 既存のデータモデル設計資料がない場合、**物理ER図と項目一覧のドラフトまで**が現実的な到達点。
> - 図は自動配置のため、オブジェクト数が多いと重なり・レイアウト崩れが出やすい。最終調整は手作業を想定。
> - 俯瞰用の1枚ものとして位置付ける。詳細はオブジェクト定義書を参照。

### B-1: docs/catalog/ フォルダの確認

```bash
python -c "
import pathlib
catalog = pathlib.Path('docs/catalog')
index = catalog / '_index.md'
model = catalog / '_data-model.md'
print('index:', index.exists())
print('model:', model.exists())
"
```

両ファイルが存在しない場合: 「`docs/catalog/` が見つかりません。先に `/sf-memory` を実行してください。」と伝えて終了。

### B-2: 生成

業務フロー図と同じフォルダ（`{ROOT}/業務フロー図/`）に出力する:
```bash
python c:\ClaudeCode\scripts\python\sf-doc-mcp\generate_data_model.py \
  --docs-dir "{カレントディレクトリ}/docs" \
  --output-dir "{ROOT}/業務フロー図" \
  --author "{作成者名}"
```

完了後、出力パスを表示:
- `{ROOT}/業務フロー図/データモデル定義書.pptx`

---

## Step C: オブジェクト定義書

### C-1: 接続先の選択

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

### C-2: 新規 or 更新の自動判定

`{ROOT}/オブジェクト定義書/` 内の `オブジェクト項目定義書_v*.xlsx` を確認する:

**既存ファイルがある場合:**
ファイル名を表示したあと、AskUserQuestion でバージョン種別を選択:
- label: "マイナー更新（vX.Y → vX.Y+1）"、description: "変更箇所を赤字表示"
- label: "メジャー更新（vX.Y → vX+1.0）"、description: "赤字をリセットして黒字化"

**既存ファイルがない場合:**
「新規作成モード（v1.0）で進めます」と表示して C-5 へ。

### C-5: システム名称

**新規作成の場合のみ** AskUserQuestion で聞く:
- label: "スキップ" description: "システム名称なしで作成"
- label: "入力する" description: "システム名称を指定する"（Otherで自由入力）

「入力する」または Other が選ばれた場合はテキストで入力してもらう。
更新の場合はこのステップをスキップ（前回の値を自動引き継ぎ）。

### C-6: 対象オブジェクトの選択

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

### C-7: 確認して生成

設定内容を表示し、AskUserQuestion で確認:
- label: "生成する"、description: "定義書の生成を開始する"
- label: "キャンセル"、description: "中止する"

「生成する」が選ばれたら出力先サブフォルダを作成してから実行:

```bash
mkdir -p "{ROOT}/オブジェクト定義書"
```

**SF CLI エイリアスで接続する場合（target-org あり）:**
```bash
python c:\ClaudeCode\scripts\python\sf-doc-mcp\generate.py \
  --sf-alias {SF_ALIAS} \
  --objects {オブジェクトリスト} \
  --output-dir "{ROOT}/オブジェクト定義書" \
  --author "{作成者名}" \
  --system-name "{システム名称}" \
  --source-file "{ROOT}/オブジェクト定義書/{既存ファイル名（新規は省略）}" \
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
  --output-dir "{ROOT}/オブジェクト定義書" \
  --author "{作成者名}" \
  --system-name "{システム名称}" \
  --source-file "{ROOT}/オブジェクト定義書/{既存ファイル名（新規は省略）}" \
  --version-increment {minor または major}
```

### C-8: 完了案内

出力パスを表示する。

ブラウザログインを使った場合（SF_ALIAS=_doc-tmp）は後処理として実行:
```bash
sf org logout --target-org _doc-tmp --no-prompt
```

内容について質問があれば対応する。

---

## Step D: 機能別設計書（機能一覧 ＋ 機能設計書）

### D-1: 出力フォルダの準備

```bash
mkdir -p "{ROOT}/機能別設計書"
```

`output_dir` = `{ROOT}/機能別設計書`、`tmp_dir` = `{ROOT}/機能別設計書/.tmp` として以降の処理に使用する。

### D-2: force-app/ をスキャンして機能一覧を取得

```bash
python c:\ClaudeCode\scripts\python\sf-doc-mcp\scan_features.py \
  --project-dir "{カレントディレクトリ}"
```

スキャン結果を表示し、AskUserQuestion で確認:
- label: "全機能を生成する"、description: "スキャンで検出された全機能の設計書を生成"
- label: "特定の機能を選択する"、description: "次のメッセージで機能IDまたは名前を入力"

「特定の機能を選択する」の場合はテキストで入力してもらい、対象を絞り込む。

### D-3: sf-design-writer エージェントへ委譲

以下の情報を self-contained なプロンプトとして `sf-design-writer` エージェントに渡す:

渡す情報:
- `project_dir`: カレントディレクトリのフルパス
- `output_dir`: `{ROOT}/機能別設計書`（apex/ flow/ lwc/ batch/ はこの中に生成される）
- `tmp_dir`: `{ROOT}/機能別設計書/.tmp`
- `author`: 作成者名
- `project_name`: プロジェクト名
- `sf_alias`: Step C で使用した SF エイリアス（Step C をスキップした場合は `.sf/config.json` から取得）
- `feature_list`: D-2 で取得したコンポーネント一覧（JSON 全文）
- `target_ids`: 対象の機能ID・API名リスト（全機能の場合は全件）
- sf-design-writer エージェント定義の全文

エージェントは以下を実行して完了報告を返す:
- 各コンポーネントのソースを徹底的に読んで設計 JSON を生成
- 機能設計書 Excel を生成（機能数分）
- 機能一覧 Excel を生成（1ファイル）
- 一時ファイルを削除

### D-4: 完了報告の表示

エージェントからの完了報告をそのまま表示する。
