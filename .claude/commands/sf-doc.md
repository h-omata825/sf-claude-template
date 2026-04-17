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
| 機能別設計書 | `force-app/`（Apex/Flow/LWC を直接スキャン）<br>`docs/design/`（既存設計書があれば参照・任意） | `/sf-retrieve` | standard または all |

> **新規オブジェクト追加後**: `/sf-memory` カテゴリ2 を再実行 → _index.md に反映  
> **新規コンポーネント追加後**: `/sf-retrieve` を再実行 → force-app/ に反映

---

## Step 0: 資料種別の選択

AskUserQuestion で作成する資料を選択（**上流 → 下流** の順）:

| # | 資料 | 出力 | 分岐 |
|---|---|---|---|
| 0 | 全て                       | 全資料を順番に生成（A→B→C→D）                                  | Step A〜D |
| 1 | プロジェクト概要書          | PPTX 2ファイル（業務フロー図 + データモデル定義書）            | Step A→B |
| 2 | オブジェクト定義書          | Excel（オブジェクト項目定義書）                                 | Step C |
| 3 | 機能別設計書                | Excel（機能一覧＋機能別設計書）                                 | Step D |

AskUserQuestion のツールを使い、以下の **4つ** を choices に含めて提示する:

- 全て — 全資料を順番に生成（A→B→C→D）
- プロジェクト概要書 — 業務フロー図 + データモデル定義書（ER図）→ PPTX 2ファイル（Step A→B の順）
- オブジェクト定義書 — オブジェクト・項目定義書 → Excel
- 機能別設計書 — 機能一覧 & 機能別設計書 → Excel

**「全て」選択時の実行順序（この順番に従うこと）:**

```
Step A（業務フロー図 PPTX）→ Step B（データモデル定義書 PPTX）→ Step C（オブジェクト定義書 Excel）→ Step D（機能別設計書 Excel）
```

「プロジェクト概要書」→ Step A 完了後そのまま Step B を実行する。

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
known = ['プロジェクト概要書', 'オブジェクト定義書', '機能別設計書']
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
mkdir -p "{ROOT}/プロジェクト概要書"
python scripts/python/sf-doc-mcp/generate_project_doc.py \
  --docs-dir "{カレントディレクトリ}/docs" \
  --output-dir "{ROOT}/プロジェクト概要書" \
  --author "{作成者名}"
```

完了後、出力パスを表示:
- `{ROOT}/プロジェクト概要書/業務フロー図.pptx`

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

- `_index.md` が存在しない場合: 「`docs/catalog/_index.md` が見つかりません。先に `/sf-memory` を実行してください。」と伝えて終了。
- `_data-model.md` が存在しない場合: 「`docs/catalog/_data-model.md` が見つかりません。先に `/sf-memory` カテゴリ2 を実行してください。」と伝えて終了。

### B-2: 生成

```bash
python scripts/python/sf-doc-mcp/generate_data_model.py \
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
python scripts/python/sf-doc-mcp/generate.py \
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

> generate.py 側でこの記録が未実装の場合は、完了後に手動で改版履歴シートに追記すること。

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
   ※ これにより force-app/ が更新される。scan_features.py は force-app/ を直接読むため、
     新規追加・削除されたコンポーネントを正しく検出するには /sf-retrieve が必須。
2. /sf-memory を実行（カテゴリ4「設計・機能仕様」を選択）
   ※ docs/design/ の既存設計書 MD を更新し、差分検出に使う参照情報を最新化する。
```

### D-1: 出力フォルダの準備

```bash
mkdir -p "{ROOT}/機能別設計書"
```

`output_dir` = `{ROOT}/機能別設計書`、`tmp_dir` = `{ROOT}/機能別設計書/.tmp` として以降の処理に使用する。

### D-2: force-app/ をスキャンして対象を確定

```bash
python scripts/python/sf-doc-mcp/scan_features.py \
  --project-dir "{カレントディレクトリ}" \
  --output "{tmp_dir}/feature_list.json"
```

> **ソースについて**: スキャン対象は `force-app/` ディレクトリ。docs ではなくメタデータを直接読むため、最終 `/sf-retrieve` 時点の内容が対象になる。新規作成したコンポーネントは `/sf-retrieve` を再実行してから本コマンドを実行すること。
> 更新時も同様に force-app/ を再スキャンするため、追加・削除されたコンポーネントは自動検出される。

スキャン結果を表示し、AskUserQuestion で対象を選択:
- label: "全て（{n}件）"、description: "スキャンで検出された全コンポーネントの設計書を生成"
- label: "対象を絞り込む"、description: "API名・機能IDをテキストで指定する"

「対象を絞り込む」が選ばれた場合はチャットで入力してもらい、対象を絞り込む。
区切り文字は何でもOK（スペース・カンマ・改行・全角スペース等）。API名・機能ID（F-001等）どちらでも受け付ける。

**対象が確定したら** AskUserQuestion で最終確認:

**質問**: 「設計書を生成します（対象: {n}件）。よろしいですか？」

- label: "生成開始"、description: "{n}件の設計書を生成する"
- label: "キャンセル"、description: "中止する"

「キャンセル」が選ばれた場合は終了。「生成開始」が選ばれたら D-3 へ進む。

**バージョンインクリメントの確認**（D-3 委譲前に一度だけ実施）:

`{output_dir}/` 配下に既存の xlsx があるか確認する:
```bash
python -c "
import pathlib, sys
xlsxs = list(pathlib.Path(r'{output_dir}').rglob('*.xlsx'))
print('exists' if xlsxs else 'new')
"
```

- 既存 xlsx がある場合のみ AskUserQuestion で選択:
  - label: "マイナー更新（変更箇所を赤字表示）"
  - label: "メジャー更新（赤字をリセット・黒字化）"
- 既存 xlsx がない場合（初回生成）: `version_increment = "minor"` として固定（スクリプト側が自動で v1.0 から開始する）

### D-3: エージェントへ委譲

feature_list のコンポーネント種別に応じて、以下の順序でエージェントに委譲する。

**共通で渡す情報**:
- `project_dir`: カレントディレクトリのフルパス
- `output_dir`: `{ROOT}/機能別設計書`
- `tmp_dir`: `{ROOT}/機能別設計書/.tmp`
- `author`: 作成者名
- `project_name`: プロジェクト名
- `version_increment`: 上記で確定した値（`minor` または `major`）
- `sf_alias`: Step C で使用した SF エイリアス（Step C をスキップした場合は `.sf/config.json` から取得）。将来の組織直接接続機能（メタデータ取得等）のために渡す。現在のスクリプト（generate_feature_design.py 等）では未使用
- `target_ids`: 対象の機能ID・API名リスト

**D-3a: LWC・画面フロー・Aura・Visualforce が含まれる場合 → `sf-screen-writer` を先に呼ぶ**

feature_list のうち `type` が `LWC` / `画面フロー` / `Aura` / `Visualforce` のもののみを抽出して渡す。
sf-screen-writer は Phase 2（Excel生成）まで実行して完了報告を返す（機能一覧・クリーンアップは行わない）。

sf-screen-writer が失敗または部分完了で返った場合:
- 完了報告で「未完了: {n}件（{コンポーネント名リスト}）」を明示する
- D-3b へ進む前にユーザーに確認を取る（「一部未完了のまま続けるか、中止するか」）
- ユーザーが続行を選んだ場合のみ D-3b へ進む

**D-3b: `sf-design-writer` を呼ぶ（常に実行）**

feature_list のうち `type` が `Apex` / `Batch` / `Flow` / `Integration` / `Trigger` のものを渡す（LWC/画面フロー/Aura/Visualforceは除外）。
sf-design-writer は以下を実行して完了報告を返す:
- Apex/Batch/Flow/Integration/Trigger の設計 JSON 生成と Excel 生成
- Phase 3: tmp_dir 内の全 design JSON（sf-screen-writer 分も含む）から機能一覧 Excel を生成
- Phase 4: tmp_dir クリーンアップ

> LWC/画面フローのみのプロジェクトで Apex が存在しない場合も、sf-design-writer を呼んで Phase 3（機能一覧生成）と Phase 4（クリーンアップ）を実行させること。

### D-4: 完了報告の表示

各エージェントからの完了報告をまとめて表示する。
