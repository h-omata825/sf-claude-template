Salesforce プロジェクトの設計書を生成します。

**基本設計 / 詳細設計 / プログラム設計** の3層構成に対応しています。

**AskUserQuestion のルール（厳守）:**
- **1質問1回答**: 複数の質問を1つの AskUserQuestion にまとめない。必ず1問ずつ順番に聞く
- **選択肢はデフォルト/スキップ値のみ**: choices に「Other」「自由入力」等は含めない
- テキスト入力（パス・名前等）はチャットで直接聞く

---

## 3層設計の概要

| 層 | 対象読者 | 内容 | 出力先 |
|---|---|---|---|
| 基本設計 | 業務担当者・PM | 誰が・何のために・どう使うか・業務フロー | `{ROOT}/基本設計書/` |
| 詳細設計 | エンジニア | コンポーネント仕様・インターフェース・画面項目 | `{ROOT}/詳細設計書/` |
| プログラム設計 | 実装者 | SOQL・DML・メソッド呼び出しの詳細・フローチャート | `{ROOT}/プログラム設計書/` |

---

## Step 0: 設計書種別の選択

AskUserQuestion で生成する設計書を選択する:

- 全て — 基本設計 → 詳細設計 → プログラム設計 の順で生成
- 基本設計 — 業務グループ単位の基本設計書（業務目的・業務フロー・構成コンポーネント）
- 詳細設計 — 業務グループ単位の詳細設計書（コンポーネント仕様・インターフェース・画面項目）
- プログラム設計 — コンポーネント単位のプログラム設計書（処理フロー・SOQL・DML）

---

## Step 0-2: 共通情報の取得

### プロジェクトディレクトリ

**最初に**チャットで直接聞く（force-app/ があるフォルダ）:
```
プロジェクトルートのパスを入力してください（force-app/ があるフォルダ）:
```

### 前回設定の読み込み

project_dir が確定したら設定ファイルを読む:

```bash
python -c "
import pathlib
try:
    import yaml
    p = pathlib.Path(r'{project_dir}') / 'docs' / 'sf_design_config.yml'
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

### 管理フォルダ

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
known = ['基本設計書', '詳細設計書', 'プログラム設計書']
for part in [p] + list(p.parents):
    if part.name in known:
        print('ROOT:' + str(part.parent))
        sys.exit()
print('ROOT:' + str(p))
"
```
出力の `ROOT:` 以降を `ROOT` として控える。

### 作成者名

**前回値がある場合:** AskUserQuestion で提示（2択+Other自動）:
- label: "前回: {last_author}"、description: "前回と同じ作成者名を使用"
- label: "スキップ"、description: "作成者名なし"

**前回値がない場合:** AskUserQuestion で提示（1択+Other自動）:
- label: "スキップ"、description: "作成者名なし"

Other が選ばれた場合はチャットで入力してもらう。「スキップ」が選ばれた場合は空文字として扱う。

### 設定の保存

確定した値を保存する（次回のデフォルト値として使用）:
```bash
python -c "
import pathlib
try:
    import yaml
    p = pathlib.Path(r'{project_dir}') / 'docs' / 'sf_design_config.yml'
    p.parent.mkdir(parents=True, exist_ok=True)
    data = {'author': r'{author}', 'output_dir': r'{ROOT}'}
    p.write_text(yaml.dump(data, allow_unicode=True, default_flow_style=False), encoding='utf-8')
except Exception as e:
    print('設定の保存に失敗:', e)
"
```

---

## Step 1: 基本設計（選択した場合）

```bash
mkdir -p "{ROOT}/基本設計書"
```

`output_dir` = `{ROOT}/基本設計書`、`tmp_dir` = `{ROOT}/基本設計書/.tmp`

### feature_groups.yml の確認・生成

```bash
python -c "
import pathlib
p = pathlib.Path(r'{project_dir}') / 'docs' / 'feature_groups.yml'
print('exists' if p.exists() else 'not_found')
"
```

なければ生成する:
```bash
python {project_dir}/scripts/python/sf-doc-mcp/group_features.py \
  --project-dir "{project_dir}" \
  --output "{project_dir}/docs/feature_groups.yml"
```

### 対象グループの選択

feature_groups.yml の内容を表示して確認してもらう:
```bash
python -c "
import yaml, json
with open(r'{project_dir}/docs/feature_groups.yml', encoding='utf-8') as f:
    groups = yaml.safe_load(f)
for g in groups:
    print(f\"{g['group_id']}: {g['name_ja']} ({len(g.get('feature_ids', []))}コンポーネント)\")
"
```

AskUserQuestion で対象を選択する:
- 全グループ — feature_groups.yml に含まれる全グループを処理
- 特定のグループのみ — グループIDをカンマ区切りで入力（次の質問で聞く）

「特定のグループのみ」を選択した場合は、チャットでグループIDを聞く:
```
対象グループIDをカンマ区切りで入力してください（例: GRP-001,GRP-003）:
```

### sf-basic-design-writer に委譲

以下の情報を渡して **sf-basic-design-writer** エージェントを起動する:

```
project_dir:      {project_dir}
output_dir:       {ROOT}/基本設計書
tmp_dir:          {ROOT}/基本設計書/.tmp
author:           {author}
project_name:     {project_name}
target_group_ids: {target_group_ids}  # 全グループの場合は空リスト []
version_increment: minor
```

---

## Step 2: 詳細設計（選択した場合）

```bash
mkdir -p "{ROOT}/詳細設計書"
```

`output_dir` = `{ROOT}/詳細設計書`、`tmp_dir` = `{ROOT}/詳細設計書/.tmp`

feature_groups.yml の確認・グループ選択は Step 1 と同じ手順で行う（Step 1 を実行済みの場合はスキップ）。

### sf-detail-design-writer に委譲

以下の情報を渡して **sf-detail-design-writer** エージェントを起動する:

```
project_dir:      {project_dir}
output_dir:       {ROOT}/詳細設計書
tmp_dir:          {ROOT}/詳細設計書/.tmp
author:           {author}
project_name:     {project_name}
target_group_ids: {target_group_ids}
version_increment: minor
```

---

## Step 3: プログラム設計（選択した場合）

> プログラム設計書と合わせて **機能一覧**（全コンポーネントの索引 Excel）も自動生成される。

```bash
mkdir -p "{ROOT}/プログラム設計書"
```

`output_dir` = `{ROOT}/プログラム設計書`、`tmp_dir` = `{ROOT}/プログラム設計書/.tmp`

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

AskUserQuestion で対象を選択する:
- 全機能 — スキャンで検出した全コンポーネントを処理
- 特定のIDのみ — 機能IDをカンマ区切りで入力

### 処理の分岐（エージェントへの委譲）

スキャン結果を **Apex/Batch/Flow(非画面)/Integration** と **LWC/画面フロー/Visualforce/Aura** に分類し、それぞれのエージェントに委譲する。

**Apex・Batch・Flow(非画面)・Integration → sf-design-writer に委譲:**
```
project_dir:       {project_dir}
output_dir:        {ROOT}/プログラム設計書
tmp_dir:           {ROOT}/プログラム設計書/.tmp
author:            {author}
project_name:      {project_name}
sf_alias:          {sf_alias}
feature_list:      {feature_list}（上記で絞り込み済みのリスト）
target_ids:        {target_ids}
version_increment: minor
```

テンプレートパス:
- Apex/Flow/Batch/Integration: `{project_dir}/scripts/python/sf-doc-mcp/プログラム設計書テンプレート.xlsx`
- LWC/画面フロー/VF/Aura: `{project_dir}/scripts/python/sf-doc-mcp/プログラム設計書（画面）テンプレート.xlsx`

**LWC・画面フロー・Visualforce・Aura → sf-screen-writer に委譲:**
```
project_dir:       {project_dir}
output_dir:        {ROOT}/プログラム設計書
tmp_dir:           {ROOT}/プログラム設計書/.tmp
author:            {author}
project_name:      {project_name}
feature_list:      {feature_list}（画面系のみに絞り込み）
target_ids:        {target_ids}
version_increment: minor
```

---

## 完了報告

```
✅ 設計書生成完了

【基本設計】（生成した場合）
  生成先: {ROOT}/基本設計書/
  生成数: {n} グループ

【詳細設計】（生成した場合）
  生成先: {ROOT}/詳細設計書/
  生成数: {n} グループ

【プログラム設計】（生成した場合）
  生成先: {ROOT}/プログラム設計書/
  生成数: {n} 件

⚠️ 要確認: ...
```

---

## 注意事項

- 基本設計・詳細設計は **グループ単位**（feature_groups.yml が必要）
- プログラム設計は **コンポーネント単位**（scan_features.py の出力が必要）
- 「全て」を選択した場合は **基本設計 → 詳細設計 → プログラム設計** の順で実行する
- `sf_alias` が不明な場合は `{project_dir}/.sf/config.json` または `sfdx-project.json` から取得する
