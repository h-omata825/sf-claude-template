Salesforceプロジェクト資料を会話形式で作成します。
スクリプトは `scripts/python/sf-doc-mcp/`（プロジェクトルートからの相対パス）にあります。

**AskUserQuestion のルール（厳守）:**
- **1質問1回答**: 複数の質問を1つの AskUserQuestion にまとめない。必ず1問ずつ順番に聞く
- **選択肢はデフォルト/スキップ値のみ**: AskUserQuestion には自動で「Other（自由入力）」が付く。choices に Other・「自由入力」・「手動入力」等の選択肢を**絶対に含めない**。「スキップ」「デフォルト値を使う」等のみ記載する
- テキスト入力（パス・名前等）はチャットで直接聞く。AskUserQuestion は使わない

---

## 前提: 情報源と依存関係

各資料が使う情報源と、最新化に必要なコマンド・選択肢。  
各 Step の冒頭でも確認を促すが、事前に把握しておくこと。

| 資料 | 情報源 | 最新化コマンド | 選択肢 |
|---|---|---|---|
| 業務フロー図 | `docs/overview/org-profile.md`<br>`docs/requirements/requirements.md`<br>`docs/architecture/system.json`<br>`docs/flow/usecases.md`<br>`docs/flow/swimlanes.json` | `/sf-memory` | **カテゴリ1: 組織概要・環境情報** |
| データモデル定義書 | `docs/catalog/_index.md`<br>`docs/catalog/_data-model.md`<br>`docs/catalog/custom/*.md`<br>`docs/catalog/standard/*.md`<br>（会社名のみ org-profile.md も参照） | `/sf-memory` | **カテゴリ2: オブジェクト・項目構成** |
| オブジェクト定義書 | ① `docs/catalog/_index.md`（対象オブジェクト候補の選択のみ）<br>② **Salesforce組織に直接接続**して項目メタデータを取得（force-app/ 不要） | ① `/sf-memory` カテゴリ2<br>② 不要（実行時に接続） | カテゴリ2: オブジェクト・項目構成 |
| プログラム設計書 | `force-app/`（Apex/Flow/LWC を直接スキャン）<br>`docs/design/`（既存設計書があれば参照・任意） | `/sf-retrieve` | standard または all |

> **新規オブジェクト追加後**: `/sf-memory` カテゴリ2 を再実行 → _index.md に反映  
> **新規コンポーネント追加後**: `/sf-retrieve` を再実行 → force-app/ に反映

---

> 設計書（基本設計・詳細設計・プログラム設計・機能一覧）の生成は `/sf-design` を使用すること。

## Step 0: 資料種別の選択

AskUserQuestion で作成する資料を選択（**上流 → 下流** の順）:

AskUserQuestion のツールを使い、以下を choices に含めて提示する:

- 全て — プロジェクト概要書 + オブジェクト定義書 を順番に生成（A→B→C の順）
- プロジェクト概要書 — プロジェクト概要書 PPTX + 業務フロー図 PPTX（要 swimlanes.json）+ データモデル定義書 PPTX（Step A→B の順）
- オブジェクト定義書 — オブジェクト・項目定義書 → Excel

**「全て」選択時の実行順序（この順番に従うこと）:**

```
Step A（業務フロー図 PPTX）→ Step B（データモデル定義書 PPTX）→ Step C（オブジェクト定義書 Excel）
```

「プロジェクト概要書」→ Step A 完了後そのまま Step B を実行する。

> 設計書（基本設計・詳細設計・プログラム設計・機能一覧）の生成は `/sf-design` を使用すること。

### Step 0-2: 共通情報の取得（資料種別選択後に一度だけ聞く）

> **前提**: このコマンドは Salesforce プロジェクトルート（`force-app/` があるフォルダ）をカレントディレクトリとして実行することを想定している。カレントディレクトリが不明な場合はチャットで確認すること。

> **テキスト入力の必須ルール**: チャットでの入力を求めたら、ユーザーが返答するまで次の処理・質問には進まない。

#### 前回設定の読み込み

```bash
python -c "
import pathlib
try:
    import yaml
    p = pathlib.Path('docs/sf_doc_config.yml')
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

出力から `author`（前回の作成者名）と `output_dir`（前回の管理フォルダ）を控える。

#### 管理フォルダ

**前回値がある場合:** AskUserQuestion で提示（1択+Other自動）:
- label: "前回: {last_output_dir}"、description: "前回と同じ管理フォルダを使用"

Other が選ばれた場合はチャットで入力:
```
資料の管理フォルダパスを入力してください:
```

**前回値がない場合:** チャットで直接聞く:
```
資料の管理フォルダパスを入力してください:
```

入力後、ROOT 解決スクリプトを実行:
```bash
python -c "
import pathlib, sys
p = pathlib.Path(r'{入力値}')
# 既知のサブフォルダ名が入力パスの途中に含まれていたら、その親をROOTとする
# 例: 'C:/work/プロジェクト概要書' → ROOT = 'C:/work'
# 例: 'C:/work/output/' → ROOT = 'C:/work/output' (調整なし)
known = ['プロジェクト概要書', 'オブジェクト定義書']
for part in [p] + list(p.parents):
    if part.name in known:
        root = part.parent
        print('ADJUSTED:' + str(root))
        sys.exit()
print('ROOT:' + str(p))
"
```
出力が `ADJUSTED:` で始まる場合は、その値を ROOT として使用し「{調整後パス} を管理フォルダとして使用します」と伝える。`ROOT:` の場合はそのまま ROOT として使用する。

#### 作成者名

**前回値がある場合:** AskUserQuestion で提示（2択+Other自動）:
- label: "前回: {last_author}"、description: "前回と同じ作成者名を使用"
- label: "スキップ"、description: "作成者名なし"

**前回値がない場合:** AskUserQuestion で提示（1択+Other自動）:
- label: "スキップ"、description: "作成者名なし"

Other が選ばれた場合はチャットで入力してもらう。「スキップ」が選ばれた場合は空文字として扱う。

#### 設定の保存

確定した値を保存する（次回のデフォルト値として使用）:
```bash
python -c "
import pathlib
try:
    import yaml
    p = pathlib.Path('docs/sf_doc_config.yml')
    p.parent.mkdir(parents=True, exist_ok=True)
    data = {'author': r'{author}', 'output_dir': r'{ROOT}'}
    p.write_text(yaml.dump(data, allow_unicode=True, default_flow_style=False), encoding='utf-8')
except Exception as e:
    print('設定の保存に失敗:', e)
"
```

> 以降の各Stepでは管理フォルダ・作成者名を再度聞かない。

---

## Step A: 業務フロー図・システム構成図（PPTX）

> - 本書の中身は **docs/ 配下の精度に完全依存** する。docs が薄いと骨組みだけのスライドになる。
> - 図（システム構成図・業務フロー図）は自動配置のため、位置・重なりに限界がある。手直しを想定すること。

**【使用する情報源】**
- `docs/overview/org-profile.md`, `docs/requirements/requirements.md` — 組織・要件情報
- `docs/architecture/system.json` — システム構成図
- `docs/flow/usecases.md`, `docs/flow/swimlanes.json` — 業務フロー図

**【最新化手順】** `/sf-memory` → カテゴリ1「組織概要・環境情報」を選択

AskUserQuestion で確認:
- label: "最新化済み・このまま続ける"
- label: "先に /sf-memory を実行する（ここで終了）"

「先に /sf-memory を実行する」が選ばれた場合: `/sf-memory` を実行してから改めて本コマンドを実行するよう案内して終了。

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
mkdir -p "{ROOT}/プロジェクト概要書"
```

**① プロジェクト概要書**（表紙・概要・システム構成図を含む PPTX）:
```bash
python "{カレントディレクトリ}/scripts/python/sf-doc-mcp/generate_project_doc.py" \
  --docs-dir "{カレントディレクトリ}/docs" \
  --output-dir "{ROOT}/プロジェクト概要書" \
  --author "{作成者名}"
```

**② 業務フロー図**（Mermaid ベース・フロー別スライド PPTX）:
```bash
python "{カレントディレクトリ}/scripts/python/sf-doc-mcp/generate_flow_pptx.py" \
  --docs-dir "{カレントディレクトリ}/docs" \
  --output-dir "{ROOT}/プロジェクト概要書" \
  --author "{作成者名}"
```

`swimlanes.json` が存在しない場合は ② をスキップし、その旨をユーザーに伝える。

完了後、出力パスを表示:
- `{ROOT}/プロジェクト概要書/プロジェクト概要書.pptx`
- `{ROOT}/プロジェクト概要書/業務フロー図.pptx`（`swimlanes.json` が存在する場合のみ）

---

## Step B: データモデル定義書

> - オブジェクト・項目・リレーション等の**事実情報はメタデータから正確に取得できる**。一方で「なぜこの項目が必要か」「オブジェクトの業務的意味」「論理ER図」は**メタデータから復元不可**。
> - 既存のデータモデル設計資料がない場合、**物理ER図と項目一覧のドラフトまで**が現実的な到達点。
> - 図は自動配置のため、オブジェクト数が多いと重なり・レイアウト崩れが出やすい。最終調整は手作業を想定。

**【使用する情報源】**
- `docs/catalog/_index.md`, `docs/catalog/_data-model.md` — オブジェクト一覧・ER図
- `docs/catalog/custom/*.md`, `docs/catalog/standard/*.md` — 各オブジェクト定義

**【最新化手順】** `/sf-memory` → カテゴリ2「オブジェクト・項目構成」を選択

AskUserQuestion で確認（「全て」の流れで来た場合も必ず確認する。Step A はカテゴリ1、Step B はカテゴリ2 で対象が異なるため）:
- label: "最新化済み・このまま続ける"
- label: "先に /sf-memory を実行する（ここで終了）"

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

- `_index.md` が存在しない場合: 「`docs/catalog/_index.md` が見つかりません。先に `/sf-memory` を実行してください。」と伝えて終了。
- `_data-model.md` が存在しない場合: 「`docs/catalog/_data-model.md` が見つかりません。先に `/sf-memory` カテゴリ2 を実行してください。」と伝えて終了。

### B-2: 生成

```bash
python "{カレントディレクトリ}/scripts/python/sf-doc-mcp/generate_data_model.py" \
  --docs-dir "{カレントディレクトリ}/docs" \
  --output-dir "{ROOT}/プロジェクト概要書" \
  --author "{作成者名}"
```

完了後、出力パスを表示:
- `{ROOT}/プロジェクト概要書/データモデル定義書.pptx`

---

## Step C: オブジェクト定義書

**【使用する情報源】**
- `docs/catalog/_index.md` — 対象オブジェクトの候補リスト表示に使用（フィールド情報には使わない）
- **Salesforce組織に直接接続**してフィールドメタデータを取得（force-app/ は不使用）

**【最新化手順】**
- `_index.md` が古い（新規オブジェクトが未反映）場合: `/sf-memory` → カテゴリ2「オブジェクト・項目構成」
- フィールドメタデータは実行時に Salesforce組織から直接取得するため、別途最新化不要

AskUserQuestion で確認:
- label: "このまま続ける"、description: "フィールドデータはSalesforce組織から直接取得するため常に最新。_index.md の更新は新規オブジェクト追加時のみ必要"
- label: "/sf-memory カテゴリ2 を実行してから続ける（終了）"、description: "Salesforceに新しいオブジェクトを追加し、選択候補に追加したい場合"

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

`docs/overview/org-profile.md` からシステム名を取得する（C-5 と同じ処理）:
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

### C-2: 新規 or 更新の自動判定

`{ROOT}/オブジェクト定義書/` 内の `オブジェクト項目定義書_v*.xlsx` を確認する:

**既存ファイルがある場合:**
ファイル名を表示したあと、AskUserQuestion でバージョン種別を選択:
- label: "マイナー更新（vX.Y → vX.Y+1）"、description: "変更箇所を赤字表示"
- label: "メジャー更新（vX.Y → vX+1.0）"、description: "赤字をリセットして黒字化"

**既存ファイルがない場合:**
「新規作成モード（v1.0）で進めます」と表示して C-3 へ。

### C-3: システム名称

新規・更新どちらでも毎回確認する。

**新規作成の場合:** `docs/overview/org-profile.md` からシステム名を取得する（`組織名`・`システム名`・`プロジェクト名` の順で検索）。
**更新の場合:** 既存ファイルの `_meta` シートから前回値を読む（`read_meta()` の `system_name` フィールド）。

AskUserQuestion で提示（1択＋Other自動）:
- 取得/読込できた場合: label: "{値}（前回/自動取得）"、description: "そのまま使用する"
- 取得できなかった場合: label: "スキップ"、description: "システム名称なし"

Other が選ばれた場合はチャットで入力してもらう。

> **重要**: 選択結果を後工程に渡す際は、label から `（前回/自動取得）` を除去した **元の値だけ** を `system_name` として使用する。ラベルの付記文字列は UI 表示用であり、資料には含めない。

### C-4: 対象オブジェクトの選択

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
m = read_meta(r'{既存ファイルのフルパス}')
if m:
    print(' '.join(m.get('objects', {}).keys()))
"
```

取得した一覧（例: `Account Opportunity Contact Knowledge__kav`）を表示したうえで、AskUserQuestion で提示（Other は自動表示）:
- label: "既存と同じ（{オブジェクト一覧}）" description: "前回と同じオブジェクトで再生成"
- label: "既存＋追加" description: "テキストで追加するオブジェクトを入力"

**「既存と同じ」選択時:** 前回のオブジェクトリストをそのまま使う。
**「既存＋追加」選択時:** テキストで追加オブジェクトを入力してもらい、既存リストに結合する。
**Other 選択時:** テキストで全オブジェクトを入力してもらう。

> 誤ってオブジェクトを消してしまわないよう、通常は「既存と同じ」または「既存＋追加」を使うこと。オブジェクト自体を削除したい場合は C-8 完了後に手動で行い、改版履歴に記録する（後述）。

区切り文字は何でもOK（スペース・カンマ・全角スペース等）。
入力内容を `--objects` に渡す（generate.py 内で名前解決する）。

**スペルチェック:** オブジェクト名に明らかなタイポ（例: Oppotunity → Opportunity）があれば、生成前に確認を取る。

### C-5: 確認して生成

設定内容を表示し、AskUserQuestion で確認:
- label: "生成する"、description: "定義書の生成を開始する"
- label: "キャンセル"、description: "中止する"

「生成する」が選ばれたら出力先サブフォルダを作成してから実行:

```bash
mkdir -p "{ROOT}/オブジェクト定義書"
```

```bash
python "{カレントディレクトリ}/scripts/python/sf-doc-mcp/generate.py" \
  --sf-alias {SF_ALIAS} \
  --objects {オブジェクトリスト} \
  --output-dir "{ROOT}/オブジェクト定義書" \
  --author "{作成者名}" \
  --system-name "{システム名称}" \
  --source-file "{ROOT}/オブジェクト定義書/{既存ファイル名（新規は省略）}" \
  --version-increment {minor または major}
```

> **ブラウザログインを使用した場合（SF_ALIAS=_doc-tmp）**: スクリプト完了・エラーのどちらでも必ず以下を実行する。エラー終了時は先に logout してから状況を報告すること。
> ```bash
> sf org logout --target-org _doc-tmp --no-prompt
> ```

### C-6: 完了案内

出力パスを表示する。

### オブジェクト・項目の削除について

オブジェクトや項目が組織から削除された場合、generate.py は対応する行・シートを **そのまま削除して出力** する。  
横線（取り消し線）は付けない。代わりに改版履歴シートに以下の形式で自動記録する:

| 改版日 | 変更種別 | 対象 | 備考 |
|---|---|---|---|
| YYYY-MM-DD | 削除 | オブジェクト名 / 項目名 | — |

> 改版履歴への自動記録が行われていない場合は、完了後に手動で改版履歴シートに追記すること。

内容について質問があれば対応する。

---

## 完了報告

各 Step の完了報告をまとめて表示する。

```
✅ 資料生成完了

【プロジェクト概要書】（生成した場合）
  生成先: {ROOT}/プロジェクト概要書/
  - プロジェクト概要書.pptx
  - 業務フロー図.pptx（swimlanes.json がある場合のみ）
  - データモデル定義書.pptx（Step B が実行された場合）

【オブジェクト定義書】（生成した場合）
  生成先: {ROOT}/オブジェクト定義書/
  - オブジェクト項目定義書_v{version}.xlsx

⚠️ 要確認: ...
```

> 設計書（プログラム設計・基本設計・詳細設計・機能一覧）の生成は `/sf-design` を使用すること。
