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

AskUserQuestion で生成する設計書を選択する:

- 全て — 詳細設計 → プログラム設計の順に生成（詳細設計 JSON をプログラム設計が参照して精度を高める）
- 詳細設計 — 機能グループ単位の詳細設計書（コンポーネント仕様・インターフェース・画面項目）
- プログラム設計 — コンポーネント単位のプログラム設計書（処理フロー・SOQL・DML）

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

### 出力先フォルダ

**前回値がある場合:** AskUserQuestion で提示（1択+Other自動）:
- label: "前回: {last_output_dir}"、description: "前回と同じフォルダを使用"

**前回値がない場合:** チャットで直接聞く:
```
資料の出力先フォルダのパスを入力してください（このフォルダ内に 02_詳細設計/ 03_プログラム設計/ が作成されます）:
```

Other が選ばれた場合もチャットで入力してもらう。確定した値を `output_dir` として控える。

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

### 設定の保存

確定した値を保存する（次回のデフォルト値として使用）:
```bash
python -c "
import pathlib
try:
    import yaml
    p = pathlib.Path('docs/.sf/sf_design_config.yml')
    p.parent.mkdir(parents=True, exist_ok=True)
    data = {'author': r'{author}', 'output_dir': r'{output_dir}'}
    p.write_text(yaml.dump(data, allow_unicode=True, default_flow_style=False), encoding='utf-8')
except Exception as e:
    print('設定の保存に失敗:', e)
"
```

---

## Step 0-3: 事前確認（「全て」選択時のみ・ここで全質問を終わらせる）

> **「全て」を選択した場合はこのセクションを実行する。** 詳細・プログラム設計で必要な対象を一括で決定し、以降の Step では一切ユーザーへの確認を行わない。

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
python {project_dir}/scripts/python/sf-doc-mcp/group_features.py \
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

### 対象グループの選択（基本・詳細・プログラム共通）

AskUserQuestion で選択する:
- 全グループ — 全グループを対象（基本・詳細・プログラム全て）
- グループIDを指定 — GRP-XXX をカンマ区切りで入力（次の質問で聞く）
- コンポーネントを指定 — Apex名・LWC名・F-XXX等で指定（次の質問で聞く）

「グループIDを指定」の場合:
```
対象グループIDをカンマ区切りで入力してください（例: GRP-001,GRP-003）:
```

「コンポーネントを指定」の場合:
```
対象コンポーネント名または機能IDをカンマ区切りで入力してください（例: QuotationRequestController,F-012）:
```

入力後、以下のスクリプトで GRP-XXX に変換する（グループ解決スクリプト）:
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

# feature_groups.yml から F-XXX → GRP-XXX マッピングを構築
with open(r'{project_dir}/docs/.sf/feature_groups.yml', encoding='utf-8') as f:
    groups = yaml.safe_load(f)
fid_to_group = {}
for g in groups:
    for fid in g.get('feature_ids', []):
        fid_to_group[fid] = g['group_id']

resolved = set()
errors = []
for inp in inputs:
    if inp.startswith('GRP-'):
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

出力の `group_id:` 以降を **`target_group_ids`** として保存する（基本・詳細・プログラム設計で共通使用）。`error:` がある場合はユーザーに確認する。

確定後、ユーザーに伝える:
```
確認完了。詳細設計 → プログラム設計の順に自動生成を開始します。以降は完了まで待機してください。
```

---

## Step 1: 詳細設計（選択した場合）

```bash
mkdir -p "{output_dir}/02_詳細設計" && mkdir -p "{output_dir}/02_詳細設計/.tmp"
```

`output_dir` = `{output_dir}/02_詳細設計`、`tmp_dir` = `{output_dir}/02_詳細設計/.tmp`

### 対象グループの選択

**「全て」モードの場合**: `target_group_ids_2 = target_group_ids`（Step 0-3 確定済み）。選択をスキップして委譲へ進む。

**単独実行の場合**:
- AskUserQuestion で選択する（全グループ / グループIDを指定 / コンポーネントを指定）
- feature_groups.yml がない場合は group_features.py を実行してから表示する

「グループIDを指定」の場合は Step 0-3 と同じグループ解決スクリプトで GRP-XXX に変換して `target_group_ids_2` とする。

### sf-detail-design-writer に委譲

以下の情報を渡して **sf-detail-design-writer** エージェントを起動する:

```
project_dir:           {project_dir}
output_dir:            {output_dir}/02_詳細設計
tmp_dir:               {output_dir}/02_詳細設計/.tmp
author:                {author}
project_name:          {project_name}
target_group_ids:      {target_group_ids_2}  # 全グループの場合は空リスト []
version_increment:     minor
```

---

## Step 2: プログラム設計（選択した場合）

> プログラム設計書と合わせて **機能一覧**（全コンポーネントの索引 Excel）も自動生成される。

```bash
mkdir -p "{output_dir}/03_プログラム設計" && mkdir -p "{output_dir}/03_プログラム設計/.tmp"
```

`output_dir` = `{output_dir}/03_プログラム設計`、`tmp_dir` = `{output_dir}/03_プログラム設計/.tmp`

### 機能スキャン

```bash
python {project_dir}/scripts/python/sf-doc-mcp/scan_features.py \
  --project-dir "{project_dir}" \
  --output "{tmp_dir}/feature_list.json"
```

スキャン結果の件数を確認する:
```bash
python -c "
import json
with open(r'{tmp_dir}/feature_list.json', encoding='utf-8') as f:
    fl = json.load(f)
print(f'スキャン完了: {len(fl)} 件')
from collections import Counter
cnt = Counter(f.get(\"type\",\"?\") for f in fl)
for t, n in sorted(cnt.items()): print(f'  {t}: {n}件')
"
```

### 対象機能の選択

**「全て」モードの場合**: Step 0-3 で確定した `target_group_ids` に属する機能IDを自動抽出する。AskUserQuestion は出さない。
```bash
python -c "
import yaml, pathlib
with open(r'{project_dir}/docs/.sf/feature_groups.yml', encoding='utf-8') as f:
    groups = yaml.safe_load(f)
target_groups = set(r'{target_group_ids}'.split(',')) if r'{target_group_ids}'.strip() else set()
fids = []
for g in groups:
    if not target_groups or g['group_id'] in target_groups:
        fids.extend(g.get('feature_ids', []))
for fid in fids:
    print(f'feature_id:{fid}')
print(f'total:{len(fids)}件')
"
```
出力の `feature_id:` 以降を `target_ids` として使用する。`target_group_ids` が空（全グループ）の場合は `target_ids = []`。

**単独実行の場合**: AskUserQuestion で対象を選択する:
- 全機能 — スキャンで検出した全コンポーネントを処理
- その他指定 — 機能IDをカンマ区切りで入力（次の質問で聞く）

> Step 2 を実行していない場合（プログラム設計のみ選択した場合）も同様に「全機能」か「その他指定」の2択。

### feature_list の読み込み

スキャン完了後、`{tmp_dir}/feature_list.json` を Read ツールで読み込み、内容を `feature_list` として保持する。

```bash
python -c "
import json
with open(r'{tmp_dir}/feature_list.json', encoding='utf-8') as f:
    fl = json.load(f)
# 種別ごとに分類して表示
apex_types = {'Apex', 'Batch', 'Integration', 'Trigger'}
screen_types = {'LWC', '画面フロー', 'Visualforce', 'Aura'}
apex_list = [f for f in fl if f.get('type') in apex_types]
screen_list = [f for f in fl if f.get('type') in screen_types]
print(f'Apex系（sf-design-writer対象）: {len(apex_list)}件')
print(f'画面系（sf-screen-writer対象）: {len(screen_list)}件')
"
```

### 処理の委譲（① sf-screen-writer → ② sf-design-writer の順）

> **実行順序は必ず守ること**: sf-design-writer の機能一覧生成は sf-screen-writer が出力した design JSON も収集するため、sf-screen-writer を先に完了させてから sf-design-writer を起動する。

**上位設計 JSON の参照**: `{output_dir}/02_詳細設計/.tmp/` に JSON が存在する場合は、その旨を**エージェント起動時に明示する**（エージェント内で自動参照する）。

**① LWC・画面フロー・Visualforce・Aura → sf-screen-writer に委譲（先に実行）:**
```
project_dir:       {project_dir}
output_dir:        {output_dir}/03_プログラム設計
tmp_dir:           {output_dir}/03_プログラム設計/.tmp
author:            {author}
project_name:      {project_name}
sf_alias:          {SF_ALIAS}
feature_list:      {feature_list}（画面系のみに絞り込み。{tmp_dir}/feature_list.json の内容）
target_ids:        {target_ids}
version_increment: minor
上位設計参照:      {output_dir}/02_詳細設計/.tmp/ に存在する JSON（なければ省略）
```

sf-screen-writer の完了を確認してから次へ進む。

**② Apex・Batch・Flow(非画面)・Integration → sf-design-writer に委譲（sf-screen-writer 完了後）:**
```
project_dir:       {project_dir}
output_dir:        {output_dir}/03_プログラム設計
tmp_dir:           {output_dir}/03_プログラム設計/.tmp
author:            {author}
project_name:      {project_name}
feature_list:      {feature_list}（Apex系のみに絞り込み。{tmp_dir}/feature_list.json の内容）
target_ids:        {target_ids}
version_increment: minor
上位設計参照:      {output_dir}/02_詳細設計/.tmp/ に存在する JSON（なければ省略）
```

sf-design-writer は機能一覧（全コンポーネント索引 Excel）も生成する。sf-screen-writer の design JSON が `{tmp_dir}` に揃っている状態で起動すること。

テンプレートパス:
- Apex/Flow/Batch/Integration: `{project_dir}/scripts/python/sf-doc-mcp/プログラム設計書テンプレート.xlsx`
- LWC/画面フロー/VF/Aura: `{project_dir}/scripts/python/sf-doc-mcp/プログラム設計書（画面）テンプレート.xlsx`

---

## 完了前クリーンアップ

全ステップ完了後、全 `.tmp` フォルダを削除する:

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
- 「全て」を選択した場合は **詳細設計 → プログラム設計** の順に逐次実行する（プログラム設計が詳細設計 JSON を参照して精度を高めるため並列化しない）
- コンポーネント名（API名・F-XXX）で対象を指定した場合は、スクリプトで対応する GRP-XXX に変換してから処理する
