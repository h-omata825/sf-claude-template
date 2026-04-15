Salesforceプロジェクト資料を会話形式で作成します。
スクリプトは `c:\ClaudeCode\scripts\python\sf-doc-mcp\` にあります。

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
| オブジェクト定義書 | ① `docs/catalog/_index.md`（対象オブジェクト候補の選択のみ）<br>② **SF組織に直接接続**して項目メタデータを取得（force-app/ 不要） | ① `/sf-memory` カテゴリ2<br>② 不要（実行時に接続） | カテゴリ2: オブジェクト・項目構成 |
| 機能別設計書 | `force-app/`（Apex/Flow/LWC を直接スキャン）<br>`docs/design/`（既存設計書があれば参照・任意） | `/sf-retrieve` | standard または all |

> **新規オブジェクト追加後**: `/sf-memory` カテゴリ2 を再実行 → _index.md に反映  
> **新規コンポーネント追加後**: `/sf-retrieve` を再実行 → force-app/ に反映

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

> **テキスト入力の必須ルール**: チャットでの入力を求めたら、ユーザーが返答するまで次の処理・質問には進まない。

**管理フォルダ**: チャットで直接聞く。AskUserQuestion は使わず、選択肢・例も表示しない:
```
資料の管理フォルダパスを入力してください:
```

入力後、ROOT 解決スクリプトを実行:
```bash
python -c "
import pathlib, sys
p = pathlib.Path(r'{入力値}')
known = ['業務フロー図', 'オブジェクト定義書', '機能別設計書']
# パス内のどこかに既知のサブフォルダ名があれば、その親を ROOT とする
for part in [p] + list(p.parents):
    if part.name in known:
        print('ROOT:' + str(part.parent))
        sys.exit()
print('ROOT:' + str(p))
"
```
出力の `ROOT:` 以降を `ROOT` として控える。  
指定値が調整された場合は「{調整後パス} を管理フォルダとして使用します」と伝える。

**作成者名**: チャットで直接聞く。AskUserQuestion は使わない:
```
作成者名を入力してください（スキップする場合は Enter または「スキップ」と入力）:
```
入力されなかった場合・「スキップ」と入力された場合は空文字として扱う。

**プロジェクト名**（機能別設計書 / 全て を選択した場合のみ）:

`docs/overview/org-profile.md` から組織名を取得する:
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
- 取得できた場合: label: "{name}"、description: "org-profile.md の組織名を使用する"
- 取得できなかった場合: label: "スキップ"、description: "プロジェクト名なし"

> 以降の各Stepでは管理フォルダ・作成者名・プロジェクト名を再度聞かない。

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

**【使用する情報源】**
- `docs/catalog/_index.md`, `docs/catalog/_data-model.md` — オブジェクト一覧・ER図
- `docs/catalog/custom/*.md`, `docs/catalog/standard/*.md` — 各オブジェクト定義

**【最新化手順】** `/sf-memory` → カテゴリ2「オブジェクト・項目構成」を選択

「全て」の流れで来た場合はこの確認をスキップする（Step A の確認で判断済みのため）。  
単独実行の場合のみ AskUserQuestion で確認:
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

**【使用する情報源】**
- `docs/catalog/_index.md` — 対象オブジェクトの候補リスト表示に使用（フィールド情報には使わない）
- **SF組織に直接接続**してフィールドメタデータを取得（force-app/ は不使用）

**【最新化手順】**
- `_index.md` が古い（新規オブジェクトが未反映）場合: `/sf-memory` → カテゴリ2「オブジェクト・項目構成」
- フィールドメタデータは実行時に SF組織から直接取得するため、別途最新化不要

AskUserQuestion で確認:
- label: "このまま続ける"、description: "フィールドデータはSF組織から直接取得するため常に最新。_index.md の更新は新規オブジェクト追加時のみ必要"
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

新規・更新どちらでも毎回確認する。

**新規作成の場合:** `docs/overview/org-profile.md` からシステム名を取得する（`組織名`・`システム名`・`プロジェクト名` の順で検索）。
**更新の場合:** 既存ファイルの `_meta` シートから前回値を読む（`read_meta()` の `system_name` フィールド）。

AskUserQuestion で提示（1択＋Other自動）:
- 取得/読込できた場合: label: "{値}（前回/自動取得）"、description: "そのまま使用する"
- 取得できなかった場合: label: "スキップ"、description: "システム名称なし"

Other が選ばれた場合はチャットで入力してもらう。

### C-6: 対象オブジェクトの選択

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
sys.path.insert(0, r'c:\ClaudeCode\scripts\python\sf-doc-mcp')
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

### オブジェクト・項目の削除について

オブジェクトや項目が組織から削除された場合、generate.py は対応する行・シートを **そのまま削除して出力** する。  
横線（取り消し線）は付けない。代わりに改版履歴シートに以下の形式で自動記録する:

| 改版日 | 変更種別 | 対象 | 備考 |
|---|---|---|---|
| YYYY-MM-DD | 削除 | オブジェクト名 / 項目名 | — |

> generate.py 側でこの記録が未実装の場合は、完了後に手動で改版履歴シートに追記すること。

ブラウザログインを使った場合（SF_ALIAS=_doc-tmp）は後処理として実行:
```bash
sf org logout --target-org _doc-tmp --no-prompt
```

内容について質問があれば対応する。

---

## Step D: 機能別設計書（機能一覧 ＋ 機能設計書）

**【使用する情報源】**
- `force-app/` — Apex/Flow/LWC を直接スキャン（docs は使わない）
- `docs/design/` — 既存設計書があれば参照（任意）

AskUserQuestion で確認:
- label: "最新化済み・このまま続ける"、description: "force-app/ と docs/design/ が最新の状態で進める"
- label: "先に最新化する"、description: "/sf-retrieve → /sf-memory Cat.4 を実行してからそのまま生成に進む"

「先に最新化する」が選ばれた場合: 以下を順番に実行し、完了後そのまま D-1 へ進む。
```
1. /sf-retrieve を実行（standard または all を選択）
2. /sf-memory を実行（カテゴリ4「設計・機能仕様」を選択）
```

### D-1: 出力フォルダの準備

```bash
mkdir -p "{ROOT}/機能別設計書"
```

`output_dir` = `{ROOT}/機能別設計書`、`tmp_dir` = `{ROOT}/機能別設計書/.tmp` として以降の処理に使用する。

### D-2: force-app/ をスキャンして対象を確定

```bash
python c:\ClaudeCode\scripts\python\sf-doc-mcp\scan_features.py \
  --project-dir "{カレントディレクトリ}"
```

> **ソースについて**: スキャン対象は `force-app/` ディレクトリ。docs ではなくメタデータを直接読むため、最終 `/sf-retrieve` 時点の内容が対象になる。新規作成したコンポーネントは `/sf-retrieve` を再実行してから本コマンドを実行すること。
> 更新時も同様に force-app/ を再スキャンするため、追加・削除されたコンポーネントは自動検出される。

スキャン結果を表示し、AskUserQuestion で対象を選択:
- label: "全て（{n}件）"、description: "スキャンで検出された全コンポーネントの設計書を生成"
- label: "対象を絞り込む"、description: "API名・機能IDをテキストで指定する"

「対象を絞り込む」が選ばれた場合はチャットで入力してもらい、対象を絞り込む。

**対象が確定したら** AskUserQuestion で最終確認:
- label: "生成開始"、description: "上記 {n}件の設計書を生成する"
- label: "キャンセル"、description: "中止する"

「キャンセル」が選ばれた場合は終了。「生成開始」が選ばれたら D-3 へ進む。

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
