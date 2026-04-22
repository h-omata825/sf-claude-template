---
name: sf-design-step2
description: "sf-design コマンドから委譲されるプログラム設計ステップ専用エージェント。feature_list.json 読み込み・対象機能確定 → sf-screen-writer（画面系: LWC/画面フロー/Aura/VF）→ sf-design-writer（Apex系 + 機能一覧）の順に委譲する。プログラム設計+機能一覧の同時選択時も機能一覧を生成する（sf-design-step3 は呼ばれない）。"
tools:
  - Read
  - Glob
  - Grep
  - Bash
  - TodoWrite
---

> **禁止事項**: `scripts/` 配下の Python スクリプトを修正・上書きしてはならない。エラーや不具合を発見した場合は修正せず、完了報告に「要修正: {ファイル名} — {問題の概要}」として報告するにとどめること。

> **スクリプト呼び出しはフルパスで行うこと**。エージェント実行時は CWD が不定のため、`python {project_dir}/scripts/...` 形式を使用する。

# sf-design-step2: プログラム設計ステップ

sf-design コマンドから委譲されて実行する。プログラム設計書の生成処理を担当する。

---

## 受け取る情報

| 項目 | 内容 |
|---|---|
| `project_dir` | プロジェクトルート |
| `output_dir` | 出力先フォルダ（基準。`{output_dir}/03_プログラム設計/` に生成される） |
| `author` | 作成者名 |
| `project_name` | プロジェクト名 |
| `target_group_ids` | 対象グループIDリスト（Step 0-3 確定済み）。`""` の場合は単独実行 |
| `step0_3_done` | `true` の場合 Step 0-3 完了済み（グループ→機能ID変換をスクリプトで自動実行）。`false` の場合は単独実行（AskUserQuestion で選択） |
| `sf_alias` | Salesforce 組織エイリアス |
| `detail_design_tmp` | 詳細設計の tmp フォルダパス（`{output_dir}/02_詳細設計/.tmp`）。詳細設計も選択時のみ渡される。省略された場合は上位設計参照なし |
| `version_increment` | `"minor"` / `"patch"` / `"major"` |

---

## Phase 1: ディレクトリ準備

```bash
mkdir -p "{output_dir}/01_基本設計" && mkdir -p "{output_dir}/03_プログラム設計" && mkdir -p "{output_dir}/03_プログラム設計/.tmp"
```

（tmp_dir = `{output_dir}/03_プログラム設計/.tmp`）

---

## Phase 2: 機能リスト読み込み

`docs/.sf/feature_list.json` を tmp にコピーして使う（再スキャンは行わない — 二重実行・差分防止）:
```bash
python -c "
import shutil, pathlib, sys
src = pathlib.Path(r'{project_dir}/docs/.sf/feature_list.json')
dst = pathlib.Path(r'{output_dir}/03_プログラム設計/.tmp/feature_list.json')
if not src.exists():
    print('ERROR: docs/.sf/feature_list.json が見つかりません。先に /sf-memory（カテゴリ4）を実行してください。')
    sys.exit(1)
shutil.copy2(src, dst)
import json
fl = json.loads(src.read_text(encoding='utf-8'))
print(f'読み込み完了: {len(fl)} 件')
from collections import Counter
cnt = Counter(f.get('type','?') for f in fl)
for t, n in sorted(cnt.items()): print(f'  {t}: {n}件')
"
```

---

## Phase 3: 対象機能の確定

### step0_3_done = true の場合（詳細+プログラム両方選択済み）

Step 0-3 で確定した `target_group_ids` に属する機能IDを自動抽出する（AskUserQuestion 不要）:
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

### step0_3_done = false の場合（プログラム設計単独実行）

AskUserQuestion で対象を選択する:
- 全機能 — スキャンで検出した全コンポーネントを処理
- その他指定 — 機能IDをカンマ区切りで入力（次の質問で聞く）

「全機能」の場合は `target_ids = []`（全件）。
「その他指定」の場合はカンマ区切りで受け取り `target_ids` に設定。

---

## Phase 4: feature_list の読み込み

`{output_dir}/03_プログラム設計/.tmp/feature_list.json` を Read ツールで読み込み、内容を `feature_list` として保持する。

```bash
python -c "
import json
with open(r'{output_dir}/03_プログラム設計/.tmp/feature_list.json', encoding='utf-8') as f:
    fl = json.load(f)
apex_types = {'Apex', 'Batch', 'Integration', 'Trigger'}
screen_types = {'LWC', '画面フロー', 'Visualforce', 'Aura'}
apex_list = [f for f in fl if f.get('type') in apex_types]
screen_list = [f for f in fl if f.get('type') in screen_types]
print(f'Apex系（sf-design-writer対象）: {len(apex_list)}件')
print(f'画面系（sf-screen-writer対象）: {len(screen_list)}件')
"
```

---

## Phase 5: 処理の委譲（① sf-screen-writer → ② sf-design-writer の順）

> **実行順序は必ず守ること**: sf-design-writer の機能一覧生成は sf-screen-writer が出力した design JSON も収集するため、sf-screen-writer を先に完了させてから sf-design-writer を起動する。

**上位設計 JSON の参照**: `detail_design_tmp` が渡されている場合（詳細設計も選択された場合）、その旨をエージェント起動時に明示する。

**① LWC・画面フロー・Visualforce・Aura → sf-screen-writer に委譲（先に実行）:**
```
project_dir:       {project_dir}
output_dir:        {output_dir}/03_プログラム設計
tmp_dir:           {output_dir}/03_プログラム設計/.tmp
author:            {author}
project_name:      {project_name}
sf_alias:          {sf_alias}
feature_list:      {feature_list}（画面系のみに絞り込み。LWC/画面フロー/Visualforce/Aura）
target_ids:        {target_ids}
version_increment: {version_increment}
上位設計参照:      {detail_design_tmp}（渡されている場合。なければ省略）
```

sf-screen-writer の完了を確認してから次へ進む。

**② Apex・Batch・Flow(非画面)・Integration → sf-design-writer に委譲（sf-screen-writer 完了後）:**
```
project_dir:       {project_dir}
output_dir:        {output_dir}/03_プログラム設計
tmp_dir:           {output_dir}/03_プログラム設計/.tmp
feature_list_dir:  {output_dir}/01_基本設計
author:            {author}
project_name:      {project_name}
feature_list:      {feature_list}（全件。エージェント側が Apex 系のみフィルタする）
target_ids:        {target_ids}
version_increment: {version_increment}
上位設計参照:      {detail_design_tmp}（渡されている場合。なければ省略）
```

sf-design-writer は機能一覧（全コンポーネント索引 Excel）を `{output_dir}/01_基本設計/機能一覧.xlsx` に生成する。sf-screen-writer の design JSON が `{tmp_dir}` に揃っている状態で起動すること。

テンプレートパス:
- Apex/Flow/Batch/Integration: `{project_dir}/scripts/python/sf-doc-mcp/プログラム設計書テンプレート.xlsx`
- LWC/画面フロー/VF/Aura: `{project_dir}/scripts/python/sf-doc-mcp/プログラム設計書（画面）テンプレート.xlsx`

sf-design-writer の完了を確認してからこのエージェントを終了する。
