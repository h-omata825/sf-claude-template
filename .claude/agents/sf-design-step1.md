---
name: sf-design-step1
model: opus
description: "sf-design コマンドから委譲される詳細設計ステップ専用エージェント。グループ確定・詳細設計の実行・必要に応じた後続エージェント（sf-design-step2/step3）への連鎖呼び出しを担う。"
tools:
  - Read
  - Glob
  - Grep
  - Bash
  - TodoWrite
---

> **禁止事項**: `scripts/` 配下の Python スクリプトを修正・上書きしてはならない。エラーや不具合を発見した場合は修正せず、完了報告に「要修正: {ファイル名} — {問題の概要}」として報告するにとどめること。

> **スクリプト呼び出しはフルパスで行うこと**。エージェント実行時は CWD が不定のため、`python {project_dir}/scripts/...` 形式を使用する。

# sf-design-step1: 詳細設計ステップ

sf-design コマンドから委譲されて実行する。グループ確定 → 詳細設計書生成 → 後続エージェント連鎖呼び出しを担当する。

---

## 受け取る情報

| 項目 | 内容 |
|---|---|
| `project_dir` | プロジェクトルート |
| `output_dir` | 出力先フォルダ（基準。`{output_dir}/02_詳細設計/` に生成される） |
| `author` | 作成者名 |
| `project_name` | プロジェクト名 |
| `version_increment` | `"minor"` / `"patch"` / `"major"` |
| `selected_steps` | 選択された種別リスト（例: `["詳細設計", "プログラム設計"]`） |

---

## Phase 1: ディレクトリ準備

```bash
mkdir -p "{output_dir}/02_詳細設計" && mkdir -p "{output_dir}/02_詳細設計/.tmp"
```

---

## Phase 2: 対象グループの確定

`feature_ids.yml` の存在確認:
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

`feature_groups.yml` を生成:
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

AskUserQuestion で選択する:
- 全グループ — 全グループを対象
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

入力後、グループ解決スクリプトで FG-XXX に変換して `target_group_ids` に設定:
```bash
python -c "
import yaml, sys, pathlib
inputs = [x.strip() for x in '{入力値}'.split(',')]
fids_path = pathlib.Path(r'{project_dir}') / 'docs' / '.sf' / 'feature_ids.yml'
api_to_fid = {}
if fids_path.exists():
    data = yaml.safe_load(fids_path.read_text(encoding='utf-8')) or {}
    for feat in data.get('features', []):
        if not feat.get('deprecated', False):
            api_to_fid[feat['api_name']] = feat['id']
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
        errors.append(f'{inp}: feature_ids.yml に API 名が見つかりません')
for g in sorted(resolved):
    print(f'group_id:{g}')
for e in errors:
    print(f'error:{e}', file=sys.stderr)
"
```

`error:` がある場合はユーザーに確認する。「全グループ」を選択した場合は `target_group_ids = ""`（空文字）と設定する。

---

## Phase 3: sf-detail-design-writer に委譲

以下の情報を渡して **sf-detail-design-writer** エージェントを起動する:

```
project_dir:           {project_dir}
output_dir:            {output_dir}/02_詳細設計
tmp_dir:               {output_dir}/02_詳細設計/.tmp
author:                {author}
project_name:          {project_name}
target_group_ids:      {target_group_ids}  # 全グループの場合は空リスト []
version_increment:     {version_increment}
```

sf-detail-design-writer の完了を確認してから Phase 4 へ進む。

---

## Phase 4: 連鎖呼び出し

`selected_steps` に応じて後続エージェントを呼び出す。

### "プログラム設計" が含まれる場合 → sf-design-step2 を呼び出す

```
project_dir:       {project_dir}
output_dir:        {output_dir}
author:            {author}
project_name:      {project_name}
version_increment: {version_increment}
target_group_ids:  {target_group_ids}
step0_3_done:      true
detail_design_tmp: {output_dir}/02_詳細設計/.tmp
```

> `selected_steps` に "機能一覧" が含まれる場合も sf-design-step2 が機能一覧を生成する。sf-design-step3 は呼ばない。

### "機能一覧" のみ含まれる（"プログラム設計" は選択なし）場合 → sf-design-step3 を呼び出す

```
project_dir:       {project_dir}
output_dir:        {output_dir}
author:            {author}
project_name:      {project_name}
version_increment: {version_increment}
```

### どちらも選択なし（詳細設計のみ）

後続エージェントなし。そのまま完了する。
