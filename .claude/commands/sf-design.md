---
description: "Salesforce 設計書（基本設計・詳細設計・プログラム設計・機能一覧）を生成する。詳細設計/プログラム設計/機能一覧の3種別をマルチセレクトで選択して実行。"
---

Salesforce プロジェクトの設計書を生成します。

**詳細設計 / プログラム設計** の2層構成に対応しています。

**AskUserQuestion のルール（厳守）:**
- **1質問1回答**: 複数の質問を1つの AskUserQuestion にまとめない。必ず1問ずつ順番に聞く
- **選択肢はデフォルト/スキップ値のみ**: choices に「Other」「自由入力」等は含めない
- テキスト入力（パス・名前等）はチャットで直接聞く

---

## 2層設計の概要

| 層 | 対象読者 | 内容 | 出力先 |
|---|---|---|---|
| 詳細設計 | エンジニア | 機能グループ単位のコンポーネント仕様・インターフェース・画面項目 | `{output_dir}/02_詳細設計/` |
| プログラム設計 | 実装者 | コンポーネント単位の処理フロー・SOQL・DML | `{output_dir}/03_プログラム設計/` |

---

## Step 0: 設計書種別の選択

AskUserQuestion で生成する設計書を **multiSelect: true** で選択する:

- 詳細設計 — 機能グループ単位の詳細設計書（コンポーネント仕様・インターフェース・画面項目）
- プログラム設計 — コンポーネント単位のプログラム設計書（処理フロー・SOQL・DML）
- 機能一覧 — 機能一覧.xlsx だけを再生成（設計書は更新しない）

選択の組み合わせと実行フロー:

| 選択 | 実行フロー |
|---|---|
| 詳細設計のみ | Step 0-2 → sf-design-step1 エージェント |
| プログラム設計のみ | Step 0-2 → sf-design-step2 エージェント |
| 機能一覧のみ | Step 0-2 → sf-design-step3 エージェント |
| 詳細+プログラム設計 | Step 0-2 → Step 0-3 → sf-design-step1 → sf-design-step2 |
| 詳細設計+機能一覧 | Step 0-2 → sf-design-step1 → sf-design-step3 |
| プログラム設計+機能一覧 | Step 0-2 → sf-design-step2（機能一覧も生成） |
| 詳細+プログラム+機能一覧 | Step 0-2 → Step 0-3 → sf-design-step1 → sf-design-step2（機能一覧も生成） |

> **「プログラム設計+機能一覧」または「詳細+プログラム+機能一覧」選択時**: sf-design-step2 内の sf-design-writer が機能一覧.xlsx を生成するため、sf-design-step3 は呼ばない（二重実行防止）。

---

## Step 0-2: 共通情報の取得

### プロジェクトディレクトリ

> sf-design は **カレントディレクトリ（force-app/ / docs/ / scripts/ が存在するフォルダ）** をプロジェクトルートとして使用する。

```bash
python -c "import pathlib; print('project_dir:' + str(pathlib.Path('.').resolve()))"
```

出力の `project_dir:` 以降を **`project_dir`** として控える。

前回設定の読み込み:
```bash
python -c "
import pathlib
try:
    import yaml
    p = pathlib.Path('docs/.sf/sf_design_config.yml')
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

### 作成者名

**前回値がある場合:** AskUserQuestion で提示（2択+Other自動）:
- label: "前回: {last_author}"、description: "前回と同じ作成者名を使用"
- label: "スキップ"、description: "作成者名なし"

**前回値がない場合:** AskUserQuestion で提示（1択+Other自動）:
- label: "スキップ"、description: "作成者名なし"

Other が選ばれた場合はチャットで入力してもらう。「スキップ」が選ばれた場合は空文字として扱う。

確定後、直ちに以下を実行して値を保持する（後続でコンテキスト汚染が起きても正確な値が残るようにするため）:
```bash
python -c "import pathlib; p = pathlib.Path('docs/.sf'); p.mkdir(parents=True, exist_ok=True); p.joinpath('.author_tmp').write_text('{author}', encoding='utf-8')"
```

### 出力先フォルダ

**前回値がある場合:** AskUserQuestion で提示（1択+Other自動）:
- label: "前回: {last_output_dir}"、description: "前回と同じフォルダを使用"

**前回値がない場合:** チャットで直接聞く:
```
資料の出力先フォルダのパスを入力してください（このフォルダ内に 02_詳細設計/ 03_プログラム設計/ が作成されます）:
```

Other が選ばれた場合もチャットで入力してもらう。確定した値を `output_dir` として控える。

確定後、直ちに以下を実行して値を保持する:
```bash
python -c "import pathlib; p = pathlib.Path('docs/.sf'); p.mkdir(parents=True, exist_ok=True); p.joinpath('.output_dir_tmp').write_text(r'{output_dir}', encoding='utf-8')"
```

### バージョン種別

AskUserQuestion で選択する（1択＋Other自動）:
- label: "minor"、description: "機能追加・仕様変更（デフォルト）"
- label: "patch"、description: "軽微な修正・誤字脱字の修正"
- label: "major"、description: "大規模な変更・後方互換性のない改訂"

選択値を **`version_increment`** として保持する。Other が選ばれた場合はチャットで入力してもらう。

### プロジェクト名

`sfdx-project.json` から自動取得を試みる（`name` フィールドがない場合はプロジェクトディレクトリ名をフォールバックとして使用）:
```bash
python -c "
import json, pathlib
proj = pathlib.Path(r'{project_dir}')
p = proj / 'sfdx-project.json'
name = ''
if p.exists():
    d = json.loads(p.read_text(encoding='utf-8'))
    name = d.get('name', '') or d.get('namespace', '')
if not name:
    name = proj.name
print('project_name:' + name)
"
```

`project_name:` の値を使用する。値が不適切な場合はチャットで確認する:
```
プロジェクト名を入力してください（設計書の表紙に記載）:
```

### 接続先組織（プログラム設計が選択された場合のみ）

**プログラム設計が選択されていない場合はこのセクションをスキップする。**

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

**target-org が取得できた場合:**

`docs/overview/org-profile.md` からシステム名を取得:
```bash
python -c "
import re, pathlib
p = pathlib.Path(r'{project_dir}/docs/overview/org-profile.md')
name = ''
if p.exists():
    for line in p.read_text(encoding='utf-8').splitlines():
        m = re.search(r'system_name[:|]\s*(.+)', line)
        if m:
            name = m.group(1).strip()
            break
print(name)
"
```

AskUserQuestion で提示（1択＋Other自動）:
- システム名が取得できた場合: label: "{alias}（{system_name}）"、description: "このプロジェクトのデフォルト組織（.sf/config.json）"
- 取得できなかった場合: label: "{alias}（このプロジェクトのデフォルト組織）"、description: ".sf/config.json で設定されている組織"

> **重要**: 選択結果を `SF_ALIAS` として使用する際は、`（` より前の alias 部分だけを取り出す。`（{system_name}）` はラベル表示用であり、SF_ALIAS に含めない。

**target-org が取得できなかった場合:**
「このフォルダにはSalesforce組織が設定されていません。ブラウザでログインします」と伝え、以下を実行:
```bash
sf org login web --alias _design-tmp
```
ブラウザが開くのでログインしてもらう。完了後 `SF_ALIAS=_design-tmp` として控える。
（生成完了後に `sf org logout --target-org _design-tmp --no-prompt` で一時エイリアスを削除する）

### 設定の保存

確定した値を保存する（次回のデフォルト値として使用）:
```bash
python -c "
import pathlib
try:
    import yaml
    author_f = pathlib.Path('docs/.sf/.author_tmp')
    outdir_f = pathlib.Path('docs/.sf/.output_dir_tmp')
    author = author_f.read_text(encoding='utf-8').strip() if author_f.exists() else ''
    output_dir = outdir_f.read_text(encoding='utf-8').strip() if outdir_f.exists() else ''
    p = pathlib.Path('docs/.sf/sf_design_config.yml')
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.dump({'author': author, 'output_dir': output_dir}, allow_unicode=True, default_flow_style=False), encoding='utf-8')
    for f in [author_f, outdir_f]:
        f.unlink(missing_ok=True)
except Exception as e:
    print('設定の保存に失敗:', e)
"
```

---

## Step 0-3: 事前確認（詳細設計 AND プログラム設計が選択された場合のみ・ここで全質問を終わらせる）

> **詳細設計 AND プログラム設計が両方選択されている場合はこのセクションを実行する（機能一覧の選択有無は問わない）。** 詳細・プログラム設計で必要な対象を一括で決定し、以降のエージェントでは一切ユーザーへの確認を行わない。
> **詳細設計またはプログラム設計のいずれかのみ選択の場合はこのセクションをスキップする（各エージェント内でグループを選択する）。**

### feature_groups.yml の生成

`feature_ids.yml` が存在しない場合は先に `/sf-memory` を実行するよう案内して中断する:
```bash
python -c "
import pathlib, sys
p = pathlib.Path(r'{project_dir}') / 'docs' / '.sf' / 'feature_ids.yml'
if not p.exists():
    print('ERROR: docs/.sf/feature_ids.yml が見つかりません。先に /sf-memory を実行してください。')
    sys.exit(1)
print('OK')
"
```

```bash
python "{project_dir}/scripts/python/sf-doc-mcp/group_features.py" \
  --project-dir "{project_dir}" \
  --output "{project_dir}/docs/.sf/feature_groups.yml"
```

グループ一覧を表示:
```bash
python -c "
import yaml
with open(r'{project_dir}/docs/.sf/feature_groups.yml', encoding='utf-8') as f:
    groups = yaml.safe_load(f)
for g in groups:
    print(f\"{g['group_id']}: {g['name_ja']} ({len(g.get('feature_ids', []))}コンポーネント)\")
print(f'合計: {len(groups)} グループ')
"
```

### 対象グループの選択（詳細・プログラム設計共通）

AskUserQuestion で選択する:
- 全グループ — 全グループを対象（詳細・プログラム全て）
- グループIDを指定 — FG-XXX をカンマ区切りで入力（次の質問で聞く）
- コンポーネントを指定 — Apex名・LWC名・F-XXX等で指定（次の質問で聞く）

「グループIDを指定」の場合:
```
対象グループIDをカンマ区切りで入力してください（例: FG-001,FG-003）:
```

「コンポーネントを指定」の場合:
```
対象コンポーネント名または機能IDをカンマ区切りで入力してください（例: QuotationRequestController,CMP-012）:
```

入力後、以下のスクリプトで FG-XXX に変換する（グループ解決スクリプト）:
```bash
python -c "
import yaml, sys, pathlib
inputs = [x.strip() for x in '{入力値}'.split(',')]

# feature_ids.yml から api_name → F-XXX マッピングを構築
fids_path = pathlib.Path(r'{project_dir}') / 'docs' / '.sf' / 'feature_ids.yml'
api_to_fid = {}
if fids_path.exists():
    data = yaml.safe_load(fids_path.read_text(encoding='utf-8')) or {}
    for feat in data.get('features', []):
        if not feat.get('deprecated', False):
            api_to_fid[feat['api_name']] = feat['id']

# feature_groups.yml から F-XXX → FG-XXX マッピングを構築
with open(r'{project_dir}/docs/.sf/feature_groups.yml', encoding='utf-8') as f:
    groups = yaml.safe_load(f)
fid_to_group = {}
for g in groups:
    for fid in g.get('feature_ids', []):
        fid_to_group[fid] = g['group_id']

resolved = set()
errors = []
for inp in inputs:
    if inp.startswith('FG-'):
        resolved.add(inp)
        continue
    fid = inp if inp.startswith('F-') else api_to_fid.get(inp)
    if fid:
        grp = fid_to_group.get(fid)
        if grp:
            resolved.add(grp)
        else:
            errors.append(f'{inp}: feature_groups.yml にグループが見つかりません')
    else:
        errors.append(f'{inp}: feature_ids.yml に API 名が見つかりません（scan_features.py を先に実行してください）')

for g in sorted(resolved):
    print(f'group_id:{g}')
for e in errors:
    print(f'error:{e}', file=sys.stderr)
"
```

出力の `group_id:` 以降を **`target_group_ids`** として保存する（詳細・プログラム設計で共通使用）。`error:` がある場合はユーザーに確認する。

「全グループ」を選択した場合は `target_group_ids = ""`（空文字）として明示的に設定する。スクリプト呼び出し時に `--group-ids` 引数を省略することで全件対象となる。

確定後、ユーザーに伝える:
```
確認完了。詳細設計 → プログラム設計の順に自動生成を開始します。以降は完了まで待機してください。
```

---

## ディスパッチ: 各エージェントへの委譲

Step 0-2・Step 0-3 が完了したら、選択内容に応じて以下のエージェントを順次呼ぶ。各エージェントは self-contained なプロンプトで起動する。

### 詳細設計が選択された場合 → sf-design-step1 エージェント

```
プロジェクトフォルダパス: {project_dir}
output_dir: {output_dir}
author: {author}
project_name: {project_name}
target_group_ids: {target_group_ids}  ← Step 0-3 確定済みの値。単独実行時は "" を渡す
step0_3_done: true（詳細+プログラム両方選択時）/ false（詳細単独）
version_increment: {version_increment}
```

sf-design-step1 の完了を確認してから次へ進む。

### プログラム設計が選択された場合 → sf-design-step2 エージェント

```
プロジェクトフォルダパス: {project_dir}
output_dir: {output_dir}
author: {author}
project_name: {project_name}
target_group_ids: {target_group_ids}  ← Step 0-3 確定済みの値。単独実行時は "" を渡す
step0_3_done: true（詳細+プログラム両方選択時）/ false（プログラム単独）
sf_alias: {SF_ALIAS}
detail_design_tmp: {output_dir}/02_詳細設計/.tmp  ← 詳細設計も選択されている場合のみ記載。なければ省略
version_increment: {version_increment}
```

sf-design-step2 の完了を確認してから次へ進む。

### 機能一覧が選択され、かつプログラム設計が未選択の場合 → sf-design-step3 エージェント

> **スキップ条件**: プログラム設計が選択されている場合は sf-design-step2 内の sf-design-writer が機能一覧を生成する。この場合 sf-design-step3 は呼ばない（二重実行防止）。

```
プロジェクトフォルダパス: {project_dir}
output_dir: {output_dir}
author: {author}
project_name: {project_name}
version_increment: {version_increment}
```

---

## 完了前クリーンアップ

全エージェント完了後、全 `.tmp` フォルダを削除する:

```bash
python -c "
import shutil, pathlib
for subdir in ['02_詳細設計', '03_プログラム設計']:
    tmp = pathlib.Path(r'{output_dir}') / subdir / '.tmp'
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
        print(f'削除: {tmp}')
print('クリーンアップ完了')
"
```

---

## 完了報告

```
✅ 設計書生成完了

【機能一覧】（生成した場合）
  生成先: {output_dir}/01_基本設計/機能一覧.xlsx

【詳細設計】（生成した場合）
  生成先: {output_dir}/02_詳細設計/
  生成数: {n} グループ

【プログラム設計】（生成した場合）
  生成先: {output_dir}/03_プログラム設計/
  生成数: {n} 件

⚠️ 要確認: ...
```

---

## 注意事項

- 詳細設計は **グループ単位**（feature_groups.yml が必要）
- プログラム設計は **コンポーネント単位**（scan_features.py の出力が必要）
- 詳細設計＋プログラム設計の両方を選択した場合は **詳細設計 → プログラム設計** の順に逐次実行する（プログラム設計が詳細設計 JSON を参照して精度を高めるため並列化しない）
- コンポーネント名（API名・F-XXX）で対象を指定した場合は、Step 0-3 またはエージェント内でスクリプトにより対応する FG-XXX に変換してから処理する
