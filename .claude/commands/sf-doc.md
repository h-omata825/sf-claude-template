Salesforceプロジェクト基本設計資料を会話形式で作成します。
スクリプトは `scripts/python/sf-doc-mcp/`（プロジェクトルートからの相対パス）にあります。

**AskUserQuestion のルール（厳守）:**
- **1質問1回答**: 複数の質問を1つの AskUserQuestion にまとめない。必ず1問ずつ順番に聞く
- **選択肢はデフォルト/スキップ値のみ**: AskUserQuestion には自動で「Other（自由入力）」が付く。choices に Other・「自由入力」・「手動入力」等の選択肢を**絶対に含めない**。「スキップ」「デフォルト値を使う」等のみ記載する
- テキスト入力（パス・名前等）はチャットで直接聞く。AskUserQuestion は使わない

---

## 前提: 情報源と依存関係

各資料が使う情報源と、最新化に必要なコマンド・選択肢。  
各 Step の冒頭でも確認を促すが、事前に把握しておくこと。

| 資料 | 情報源 | 最新化コマンド |
|---|---|---|
| プロジェクト概要書 | `docs/overview/org-profile.md`<br>`docs/requirements/requirements.md`<br>`docs/architecture/system.json`<br>`docs/catalog/_data-model.md`<br>`docs/flow/swimlanes.json` | `/sf-memory` カテゴリ1・2 |
| オブジェクト定義書 | `docs/catalog/_index.md`（対象オブジェクト候補の選択のみ）<br>**Salesforce組織に直接接続**してフィールドメタデータを取得 | `/sf-memory` カテゴリ2 |

> **新規オブジェクト追加後**: `/sf-memory` カテゴリ2 を再実行 → _index.md に反映

> **機能一覧は `/sf-design` が生成する**（プログラム設計書生成と同時に `{output_dir}/01_基本設計/` へ自動出力）。

**出力先**: 全ての資料は `{output_dir}/01_基本設計/` に統一して出力する（`output_dir` は Step 0-2 で指定）。

---

> 詳細設計・プログラム設計の生成は `/sf-design` を使用すること。

## Step 0: 資料種別の選択

AskUserQuestion で作成する資料を選択（**上流 → 下流** の順）:

AskUserQuestion のツールを使い、以下を choices に含めて提示する:

- 全て — プロジェクト概要書 + オブジェクト定義書 を順番に生成（A→B の順）
- プロジェクト概要書 — プロジェクト概要書.xlsx
- オブジェクト定義書 — オブジェクト項目定義書.xlsx

**「全て」選択時の実行順序（この順番に従うこと）:**

```
Step A（プロジェクト概要書）→ Step B（オブジェクト定義書）
```

「プロジェクト概要書」→ Step A のみ実行して終了。
「オブジェクト定義書」→ Step B のみ実行して終了。

### Step 0-2: 共通情報の取得（資料種別選択後に一度だけ聞く）

> **前提**: このコマンドは Salesforce プロジェクトルート（`force-app/` があるフォルダ）をカレントディレクトリとして実行することを想定している。カレントディレクトリが不明な場合はチャットで確認すること。

まずカレントディレクトリを `project_dir` として確定する（以降の全スクリプト呼び出しで使用）:
```bash
python -c "import os, sys; sys.stdout.reconfigure(encoding='utf-8'); print(os.getcwd())"
```
出力されたパスを `{project_dir}` として保持する。以降のスクリプト呼び出しは全てこの値を使う。

> **テキスト入力の必須ルール**: チャットでの入力を求めたら、ユーザーが返答するまで次の処理・質問には進まない。

#### 前回設定の読み込み

```bash
python -c "
import pathlib
try:
    import yaml
    p = pathlib.Path('docs/.sf/sf_doc_config.yml')
    if p.exists():
        d = yaml.safe_load(p.read_text(encoding='utf-8')) or {}
        print('author:' + str(d.get('author', '')))
        print('output_dir:' + str(d.get('output_dir', '')))
    else:
        print('author:')
        print('output_dir:')
except Exception:
    print('author:')
    print('output_dir:')
"
```

出力から `author`（前回の作成者名）と `output_dir`（前回の出力先フォルダ）を控える。

#### 作成者名

**前回値がある場合:** AskUserQuestion で提示（2択+Other自動）:
- label: "前回: {last_author}"、description: "前回と同じ作成者名を使用"
- label: "スキップ"、description: "作成者名なし"

**前回値がない場合:** AskUserQuestion で提示（1択+Other自動）:
- label: "スキップ"、description: "作成者名なし"

Other が選ばれた場合はチャットで入力してもらう。「スキップ」が選ばれた場合は空文字として扱う。

#### 出力先フォルダ

**前回値がある場合:** AskUserQuestion で提示（1択+Other自動）:
- label: "前回: {last_output_dir}"、description: "前回と同じフォルダを使用"

**前回値がない場合:** チャットで直接聞く:
```
資料の出力先フォルダのパスを入力してください（このフォルダ内に 01_基本設計/ が作成されます）:
```

Other が選ばれた場合はチャットで入力してもらう。結果を `output_dir` として保持する（末尾のスラッシュは除去）。

#### 設定の保存

確定した値を保存する（次回のデフォルト値として使用）:
```bash
python -c "
import pathlib
try:
    import yaml
    p = pathlib.Path('docs/.sf/sf_doc_config.yml')
    p.parent.mkdir(parents=True, exist_ok=True)
    data = {'author': '{author}', 'output_dir': r'{output_dir}'}
    p.write_text(yaml.dump(data, allow_unicode=True, default_flow_style=False), encoding='utf-8')
except Exception as e:
    print('設定の保存に失敗:', e)
"
```

> 以降の各Stepでは作成者名を再度聞かない。

---

## Step 0-3: 事前確認（「全て」選択時のみ・ここで全質問を終わらせる）

> **「全て」を選択した場合はこのセクションを実行する。** Step A・B で必要な情報を一括収集し、以降は一切ユーザーへの確認を行わない。

### docs/ ファイル存在確認

```bash
python -c "
import pathlib
docs = pathlib.Path('docs')
required = {
    'Step A用（プロジェクト概要書）': [
        docs / 'overview' / 'org-profile.md',
        docs / 'requirements' / 'requirements.md',
    ],
    'Step B用（オブジェクト定義書）': [
        docs / 'catalog' / '_index.md',
    ],
}
optional = {
    'Step A用オプション（欠落時は該当シートが空欄）': [
        docs / 'architecture' / 'system.json',
        docs / 'flow' / 'swimlanes.json',
        docs / 'catalog' / '_data-model.md',
    ],
}
for label, paths in required.items():
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        print(f'MISSING {label}: {missing}')
    else:
        print(f'OK {label}')
for label, paths in optional.items():
    for p in paths:
        if not p.exists():
            print(f'OPTIONAL_MISSING: {p} がありません。該当シートはスキップされます')
"
```

- `MISSING Step A用` が出た場合は「先に `/sf-memory` カテゴリ1 を実行してください」と伝えて終了。
- `MISSING Step B用` が出た場合は「先に `/sf-memory` カテゴリ2 を実行してください」と伝えて終了。

### /sf-memory 最新化確認（カテゴリ1・カテゴリ2 まとめて）

AskUserQuestion で確認:
- label: "両カテゴリとも最新化済み・このまま続ける"
- label: "先に /sf-memory を実行する（ここで終了）"

「先に実行する」が選ばれた場合: `/sf-memory` を実行してから改めて本コマンドを実行するよう案内して終了。

### Step B 事前設定（オブジェクト定義書の設定）

**B-1: 接続先組織の確認**

`.sf/config.json` から target-org を取得:
```bash
python -c "
import json, pathlib
p = pathlib.Path('.sf/config.json')
if p.exists():
    d = json.loads(p.read_text(encoding='utf-8'))
    print(d.get('target-org', ''))
"
```

`org-profile.md` からシステム名を取得:
```bash
python -c "
import re, pathlib, sys
sys.stdout.reconfigure(encoding='utf-8')
p = pathlib.Path('docs/overview/org-profile.md')
if p.exists():
    text = p.read_text(encoding='utf-8')
    for pat in [r'\|\s*組織名\s*\|\s*(.+?)\s*\|', r'システム名[^\n:：]*[:：]\s*(.+)', r'プロジェクト名[^\n:：]*[:：]\s*(.+)']:
        m = re.search(pat, text)
        if m:
            print(m.group(1).strip())
            break
"
```

AskUserQuestion で提示（1択＋Other自動）:
- target-org が取得できた場合: label: "{alias}（{system_name}）"、description: "このプロジェクトのデフォルト組織"
- 取得できなかった場合: label: "ブラウザでログインする"

`SF_ALIAS` として保持する（`（` より前の alias 部分のみ）。ブラウザログインを選択した場合は後述の一時エイリアス処理を Step B 冒頭で実行。

**B-2: バージョン種別**

`{output_dir}/01_基本設計/` 内の `オブジェクト項目定義書_v*.xlsx` を確認し、**最新ファイルのフルパスを `latest_obj_file` 変数に保存する**:
```bash
python -c "
import pathlib, glob, os
files = sorted(glob.glob(r'{output_dir}/01_基本設計/オブジェクト項目定義書_v*.xlsx'), key=os.path.getmtime, reverse=True)
for f in files:
    print(f)
print('LATEST:', files[0] if files else '')
"
```

`LATEST:` 行に表示されたパスを `latest_obj_file` として記録する（後の B-4 で使用）。

既存ファイルがある場合は AskUserQuestion で選択:
- label: "マイナー更新（vX.Y → vX.Y+1）"
- label: "メジャー更新（vX.Y → vX+1.0）"

既存ファイルがない場合: `version_increment = minor`（新規）として続行。`latest_obj_file` は空とする。

**B-3: システム名称**

新規の場合は `org-profile.md` から、更新の場合は既存ファイルの `_meta` シートから取得してAskUserQuestion で確認:
- label: "{値}（前回/自動取得）"

Other の場合はチャットで入力。結果を `システム名称` として保持（`（前回/自動取得）` を除去した値のみ）。

**B-4: 対象オブジェクトの選択**

`docs/catalog/_index.md` からオブジェクト一覧を取得:
```bash
python -c "
import re, pathlib
text = pathlib.Path('docs/catalog/_index.md').read_text(encoding='utf-8')
rows = re.findall(r'\|\s*[^\|]+\|\s*([A-Za-z][A-Za-z0-9_]*)\s*\|', text)
skip = {'API名', 'キープレフィックス', 'オブジェクト', 'バージョン', '定義書'}
all_objs = list(dict.fromkeys(r.strip() for r in rows if r.strip() not in skip))
standard = [o for o in all_objs if not o.endswith('__c')]
custom   = [o for o in all_objs if o.endswith('__c')]
print(' '.join(standard + custom))
"
```

AskUserQuestion で提示:
- 新規の場合: label: "_index.md の全オブジェクト（{n}件）"
- 更新の場合: label: "既存と同じ（{オブジェクト一覧}）" / label: "既存＋追加"

Other の場合はチャットで入力。結果を `オブジェクトリスト` として保持。

### 確定・開始

「確認完了。プロジェクト概要書 → オブジェクト定義書の順に自動生成を開始します。以降は完了まで待機してください。」と伝える。

---

## Step A: プロジェクト概要書（Excel）

> - 本書の中身は **docs/ 配下の精度に完全依存** する。docs が薄いと骨組みだけになる。
> - 図エリア（システム構成図・業務フロー図・ER図）はプレースホルダーのみ。手動貼り付けを想定。

**【使用する情報源】**
- `docs/overview/org-profile.md`, `docs/requirements/requirements.md` — 組織・要件情報
- `docs/architecture/system.json` — システム構成図（外部連携先）
- `docs/catalog/_data-model.md` — オブジェクト関連情報
- `docs/flow/usecases.md` — 用語集・UC情報

**【最新化手順】** `/sf-memory` → カテゴリ1・2 を選択

**「全て」モードの場合**: Step 0-3 で確認済み。スキップして A-1 へ進む。

**単独実行の場合**: AskUserQuestion で確認:
- label: "最新化済み・このまま続ける"
- label: "先に /sf-memory を実行する（ここで終了）"

「先に /sf-memory を実行する」が選ばれた場合: `/sf-memory` を実行してから改めて本コマンドを実行するよう案内して終了。

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
    'model':     docs / 'catalog'      / '_data-model.md',
    'swimlanes': docs / 'flow'         / 'swimlanes.json',
}
for k, p in paths.items():
    print(f'{k}: {p.exists()}')
"
```

- `profile` / `req` が両方ない場合:「先に `/sf-memory` カテゴリ1 を実行してください。」と伝えて終了。
- その他が存在しない場合: 「{ファイル名} が見つかりません。該当シートはスキップ/空欄になります。」と表示して続行。

### A-2: 生成

出力先フォルダを作成してから実行:
```bash
mkdir -p "{output_dir}/01_基本設計"
```

```bash
python "{project_dir}/scripts/python/sf-doc-mcp/generate_basic_doc.py" \
  --docs-dir "{project_dir}/docs" \
  --output "{output_dir}/01_基本設計/プロジェクト概要書.xlsx" \
  --author "{作成者名}"
```

完了後、出力パスを表示:
- `{output_dir}/01_基本設計/プロジェクト概要書.xlsx`

---

## Step B: オブジェクト定義書

**【使用する情報源】**
- `docs/catalog/_index.md` — 対象オブジェクトの候補リスト表示に使用（フィールド情報には使わない）
- **Salesforce組織に直接接続**してフィールドメタデータを取得（force-app/ は不使用）

**【最新化手順】**
- `_index.md` が古い（新規オブジェクトが未反映）場合: `/sf-memory` → カテゴリ2「オブジェクト・項目構成」
- フィールドメタデータは実行時に Salesforce組織から直接取得するため、別途最新化不要

**「全て」モードの場合**: Step 0-3 で設定済み（`SF_ALIAS` / `version_increment` / `システム名称` / `オブジェクトリスト`）。B-1〜B-4 をスキップして B-5 へ進む。

**単独実行の場合**: AskUserQuestion で確認:
- label: "このまま続ける"
- label: "/sf-memory カテゴリ2 を実行してから続ける（終了）"

### B-1: 接続先の選択（単独実行時のみ）

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

`docs/overview/org-profile.md` からシステム名を取得する（B-3 と同じ処理）:
```bash
python -c "
import re, pathlib, sys
sys.stdout.reconfigure(encoding='utf-8')
p = pathlib.Path('docs/overview/org-profile.md')
if p.exists():
    text = p.read_text(encoding='utf-8')
    for pat in [r'\|\s*組織名\s*\|\s*(.+?)\s*\|', r'システム名[^\n:：]*[:：]\s*(.+)', r'プロジェクト名[^\n:：]*[:：]\s*(.+)']:
        m = re.search(pat, text)
        if m:
            print(m.group(1).strip())
            break
"
```

AskUserQuestion で提示（1択＋Other自動）:
- システム名が取得できた場合: label: "{alias}（{system_name}）"、description: "このプロジェクトのデフォルト組織（.sf/config.json）"
- 取得できなかった場合: label: "{alias}（このプロジェクトのデフォルト組織）"、description: ".sf/config.json で設定されている組織"

> **重要**: 選択結果を `SF_ALIAS` として使用する際は、`（` より前の alias 部分だけを取り出す。`（{system_name}）` はラベル表示用であり、SF_ALIAS に含めない。

**target-org が取得できなかった場合:**
「このフォルダにはSalesforce組織が設定されていません。ブラウザでログインします」と伝え、以下を実行:
```bash
sf org login web --alias _doc-tmp
```
ブラウザが開くのでログインしてもらう。完了後 `SF_ALIAS=_doc-tmp` として控える。
（生成完了後に `sf org logout --target-org _doc-tmp --no-prompt` で一時エイリアスを削除する）

### B-2: 新規 or 更新の自動判定（単独実行時のみ）

`{output_dir}/01_基本設計/` 内の `オブジェクト項目定義書_v*.xlsx` を確認する:

**既存ファイルがある場合:**
ファイル名を表示したあと、AskUserQuestion でバージョン種別を選択:
- label: "マイナー更新（vX.Y → vX.Y+1）"、description: "変更箇所を赤字表示"
- label: "メジャー更新（vX.Y → vX+1.0）"、description: "赤字をリセットして黒字化"

**既存ファイルがない場合:**
「新規作成モード（v1.0）で進めます」と表示して B-3 へ。

### B-3: システム名称（単独実行時のみ）

**新規作成の場合:** `docs/overview/org-profile.md` からシステム名を取得する（`組織名`・`システム名`・`プロジェクト名` の順で検索）。
**更新の場合:** 既存ファイルの `_meta` シートから前回値を読む（`read_meta()` の `system_name` フィールド）。

AskUserQuestion で提示（1択＋Other自動）:
- 取得/読込できた場合: label: "{値}（前回/自動取得）"、description: "そのまま使用する"
- 取得できなかった場合: label: "スキップ"、description: "システム名称なし"

Other が選ばれた場合はチャットで入力してもらう。

> **重要**: 選択結果を後工程に渡す際は、label から `（前回/自動取得）` を除去した **元の値だけ** を `system_name` として使用する。ラベルの付記文字列は UI 表示用であり、資料には含めない。

### B-4: 対象オブジェクトの選択（単独実行時のみ）

**新規作成の場合:**

まず `docs/catalog/_index.md` からオブジェクト一覧を取得する（**標準オブジェクトを先頭に、カスタムオブジェクトを後に**並べる）:
```bash
python -c "
import re, pathlib
text = pathlib.Path('docs/catalog/_index.md').read_text(encoding='utf-8')
rows = re.findall(r'\|\s*[^\|]+\|\s*([A-Za-z][A-Za-z0-9_]*)\s*\|', text)
skip = {'API名', 'キープレフィックス', 'オブジェクト', 'バージョン', '定義書'}
all_objs = list(dict.fromkeys(r.strip() for r in rows if r.strip() not in skip))
standard = [o for o in all_objs if not o.endswith('__c')]
custom   = [o for o in all_objs if o.endswith('__c')]
print(' '.join(standard + custom))
"
```

> **注意**: `/sf-memory` を再実行していない場合、新規作成したオブジェクトが _index.md に未反映の可能性がある。その場合は「Other」で手動指定するか、先に `/sf-memory` を再実行すること。

取得した一覧をもとに AskUserQuestion で提示（Other は自動表示）:
- label: "_index.md の全オブジェクト（{n}件）"、description: "最終 /sf-memory 時点の使用中オブジェクト（標準→カスタム順）"

Other が選ばれた場合はテキストで入力してもらう:
```
対象オブジェクトを入力してください（API名またはラベル名、複数可）:
```

**更新の場合:**
まず既存ファイルから前回のオブジェクト一覧を取得する:
```bash
python -c "
import sys
sys.path.insert(0, 'scripts/python/sf-doc-mcp')
from meta_store import read_meta
m = read_meta(r'{latest_obj_file}')
if m:
    print(' '.join(m.get('objects', {}).keys()))
"
```

取得した一覧を表示したうえで、AskUserQuestion で提示（Other は自動表示）:
- label: "既存と同じ（{オブジェクト一覧}）" description: "前回と同じオブジェクトで再生成"
- label: "既存＋追加" description: "テキストで追加するオブジェクトを入力"

**「既存と同じ」選択時:** 前回のオブジェクトリストをそのまま使う。
**「既存＋追加」選択時:** テキストで追加オブジェクトを入力してもらい、既存リストに結合する。
**Other 選択時:** テキストで全オブジェクトを入力してもらう。

> 誤ってオブジェクトを消してしまわないよう、通常は「既存と同じ」または「既存＋追加」を使うこと。オブジェクト自体を削除したい場合は B-5 完了後に手動で行い、改版履歴に記録する（後述）。

区切り文字は何でもOK（スペース・カンマ・全角スペース等）。
入力内容を `--objects` に渡す（generate.py 内で名前解決する）。

**スペルチェック:** オブジェクト名に明らかなタイポ（例: Oppotunity → Opportunity）があれば、生成前に確認を取る。

### B-5: 生成

**「全て」モードの場合**: Step 0-3 で確認済み。確認なしでそのまま生成を開始する。

**単独実行の場合**: AskUserQuestion で確認:
- label: "生成する"
- label: "キャンセル"

「キャンセル」が選ばれた場合は終了する。

出力先フォルダを作成してから実行:

```bash
mkdir -p "{output_dir}/01_基本設計"
```

**新規作成の場合（`--source-file` 引数をドロップする）:**
```bash
python "{project_dir}/scripts/python/sf-doc-mcp/generate.py" \
  --sf-alias {SF_ALIAS} \
  --objects {オブジェクトリスト} \
  --output-dir "{output_dir}/01_基本設計" \
  --author "{作成者名}" \
  --system-name "{システム名称}" \
  --version-increment minor
```

**更新の場合（`--source-file` に `latest_obj_file` を渡す）:**
```bash
python "{project_dir}/scripts/python/sf-doc-mcp/generate.py" \
  --sf-alias {SF_ALIAS} \
  --objects {オブジェクトリスト} \
  --output-dir "{output_dir}/01_基本設計" \
  --author "{作成者名}" \
  --system-name "{システム名称}" \
  --source-file "{latest_obj_file}" \
  --version-increment {minor または major}
```

> **ブラウザログインを使用した場合（SF_ALIAS=_doc-tmp）**: スクリプト完了・エラーのどちらでも必ず以下を実行する。エラー終了時は先に logout してから状況を報告すること。
> ```bash
> sf org logout --target-org _doc-tmp --no-prompt
> ```

### B-6: 完了案内

出力パスを表示する。

### オブジェクト・項目の削除について

オブジェクトや項目が組織から削除された場合、generate.py は対応する行・シートを **そのまま削除して出力** する。  
横線（取り消し線）は付けない。代わりに改版履歴シートに以下の形式で自動記録する:

| 改版日 | 変更種別 | 対象 | 備考 |
|---|---|---|---|
| YYYY-MM-DD | 削除 | オブジェクト名 / 項目名 | — |

> 改版履歴への自動記録が行われていない場合は、完了後に手動で改版履歴シートに追記すること。

---

## 完了報告

各 Step の完了報告をまとめて表示する。

```
✅ 資料生成完了

【生成先】{output_dir}/01_基本設計/

【プロジェクト概要書】（生成した場合）
  - プロジェクト概要書.xlsx

【オブジェクト定義書】（生成した場合）
  - オブジェクト項目定義書_v{version}.xlsx

⚠️ 要確認: ...
```
