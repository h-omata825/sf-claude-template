---
description: "Salesforce 設計書（詳細設計・プログラム設計・機能一覧）を生成する。詳細設計/プログラム設計/機能一覧の3種別をマルチセレクトで選択して実行。"
---

Salesforce プロジェクトの設計書を生成します。

**詳細設計 / プログラム設計** の2層構成に対応しています。

**AskUserQuestion のルール（厳守）:** [共通ルール参照](.claude/CLAUDE.md#askuserquestion-ルール厳守)

**テンプレート置換ルール（厳守）:** [共通ルール参照](.claude/CLAUDE.md#テンプレート置換ルール厳守) — 加えて以下の固有規則を適用する:
- **列挙値** (`{version_increment}`): `minor` / `major` 以外が指定された場合は `minor` にフォールバックし、ユーザーに「未知の値のためminorに置換」と警告する。

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

> **最低1件選択必須**: 0件選択（空配列）が返された場合は、再度 AskUserQuestion で同じ質問を提示する。3種別のいずれも生成しない無実行は許容しない。

選択の組み合わせとディスパッチ先:

| 選択 | 委譲先 | 備考 |
|---|---|---|
| 詳細設計のみ | sf-design-step1 | step1 内でグループ選択 |
| プログラム設計のみ | sf-design-step2 | step2 内でグループ選択・SF_ALIAS 取得 ※機能一覧.xlsx も自動更新 |
| 機能一覧のみ | sf-design-step3 | — |
| 詳細+プログラム設計 | sf-design-step1 | step1 内でグループ一括確定 → step2 を連鎖呼び出し ※機能一覧.xlsx も自動更新 |
| 詳細設計+機能一覧 | sf-design-step1 | step1 が詳細設計完了後 step3 を連鎖呼び出し |
| プログラム設計+機能一覧 | sf-design-step2 | step2 内で機能一覧も生成（step3 は不要） |
| 詳細+プログラム+機能一覧 | sf-design-step1 | step1 → step2（機能一覧も生成）の順に連鎖 |

> **副作用注記**: 「プログラム設計」を含む全ての選択（プログラム設計のみ / プログラム設計+機能一覧 / 詳細+プログラム / 詳細+プログラム+機能一覧）で `{output_dir}/01_基本設計/機能一覧.xlsx` が自動更新される（sf-design-writer の仕様）。意図しない上書きを避けたい場合は事前にバックアップすること。

> **詳細+プログラム選択時**: グループの一括確定と連鎖呼び出しは sf-design-step1 が担う。コマンドはディスパッチ後に step1 の完了を待つ。

---

## Step 0-2: 共通情報の取得

### プロジェクトディレクトリ

> sf-design は **カレントディレクトリ（force-app/ / docs/ / scripts/ が存在するフォルダ）** をプロジェクトルートとして使用する。

```bash
python -c "import pathlib; print('project_dir:' + str(pathlib.Path('.').resolve()))"
```

出力の `project_dir:` 以降を **`project_dir`** として控える。

前回設定の読み込み:

Read tool で `{project_dir}/docs/.sf/sf_design_config.yml` を読み取る。

- ファイルが存在しない場合（Read エラー）: `last_author = ""`、`last_output_dir = ""` として扱う
- ファイルが存在する場合: `author:` 行の値を `last_author`、`output_dir:` 行の値を `last_output_dir` として控える（値が空文字または未定義の場合は `""`）

> **重要**: ここで取得した日本語値は **絶対に `python -c` の stdout 経由で再表示・再取得しない**。Read tool で得た値をそのまま AskUserQuestion の補間に使うこと（Bash stdout のラウンドトリップで日本語値が文字化けする事例あり）。

### 作成者名

**前回値がある場合:** AskUserQuestion で提示（2択+Other自動）:
- label: "前回: {last_author}"、description: "前回と同じ作成者名を使用"
- label: "スキップ"、description: "作成者名なし"

**前回値がない場合:** チャットで直接聞く:
```
作成者名を入力してください（不要な場合は「スキップ」と返答）:
```
「スキップ」と返答された場合は空文字として扱う。

確定後、直ちに以下を実行して値を保持する（後続でコンテキスト汚染が起きても正確な値が残るようにするため）:
```bash
python -c "import pathlib; p = pathlib.Path(r'{project_dir}/docs/.sf'); p.mkdir(parents=True, exist_ok=True); p.joinpath('.author_tmp').write_text('{author}', encoding='utf-8')"
```

### 出力先フォルダ

**前回値がある場合:** AskUserQuestion で提示（2択+Other自動）:
- label: "前回: {last_output_dir}"、description: "前回と同じフォルダを使用"
- label: "別のフォルダを指定する"、description: "新しいパスをチャットで入力する"

**前回値がない場合:** チャットで直接聞く:
```
資料の出力先フォルダのパスを入力してください（このフォルダ内に 02_詳細設計/ 03_プログラム設計/ が作成されます）:
```

「別のフォルダを指定する」または Other が選ばれた場合はチャットで入力してもらう。確定した値を `output_dir` として控える。

確定後、直ちに以下を実行して値を保持する:
```bash
python -c "import pathlib; p = pathlib.Path(r'{project_dir}/docs/.sf'); p.mkdir(parents=True, exist_ok=True); p.joinpath('.output_dir_tmp').write_text(r'{output_dir}', encoding='utf-8')"
```

### バージョン種別

既存ファイルの有無で出し分ける。判定スクリプト:
```bash
python -c "
import pathlib
selected = {selected_types}
output = pathlib.Path(r'{output_dir}')
checks = []
if '詳細設計' in selected:
    checks += list((output / '02_詳細設計').glob('*.xlsx')) if (output / '02_詳細設計').exists() else []
if 'プログラム設計' in selected:
    checks += list((output / '03_プログラム設計').glob('*.xlsx')) if (output / '03_プログラム設計').exists() else []
if '機能一覧' in selected:
    p = output / '01_基本設計' / '機能一覧.xlsx'
    if p.exists(): checks.append(p)
print('HAS_EXISTING:', len(checks) > 0)
"
```

**既存ファイルが1件以上ある場合:** AskUserQuestion で選択する（2択＋Other自動）:
- label: "minor"、description: "機能追加・仕様変更・軽微な修正（デフォルト）"
- label: "major"、description: "大規模な変更・後方互換性のない改訂"

選択値を **`version_increment`** として保持する。Other が選ばれた場合はチャットで入力してもらう。

**既存ファイルが1件もない場合（新規作成）:** AskUserQuestion をスキップし、`version_increment = "minor"` を自動セット。ユーザーに「新規作成のため version を minor で自動設定しました」と1行通知する。

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
import pathlib, sys
author_f = pathlib.Path(r'{project_dir}/docs/.sf/.author_tmp')
outdir_f = pathlib.Path(r'{project_dir}/docs/.sf/.output_dir_tmp')
try:
    import yaml
    author = author_f.read_text(encoding='utf-8').strip() if author_f.exists() else ''
    output_dir = outdir_f.read_text(encoding='utf-8').strip() if outdir_f.exists() else ''
    p = pathlib.Path(r'{project_dir}/docs/.sf/sf_design_config.yml')
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.dump({'author': author, 'output_dir': output_dir}, allow_unicode=True, default_flow_style=False), encoding='utf-8')
except Exception as e:
    print('warning: 設定保存に失敗（次回デフォルト値の復元なし）:', e, file=sys.stderr)
finally:
    # 成功・失敗にかかわらず一時ファイルは必ず削除する
    for f in [author_f, outdir_f]:
        f.unlink(missing_ok=True)
"
```

---

## Step 1: ディスパッチ — 各エージェントへの委譲

Step 0-2 完了後、選択内容に応じて以下のエージェントを self-contained プロンプトで起動する。

### 詳細設計が選択された場合 → sf-design-step1 エージェント

```
プロジェクトフォルダパス: {project_dir}
output_dir: {output_dir}
author: {author}
project_name: {project_name}
version_increment: {version_increment}
selected_steps: {選択した種別のリスト。例: ["詳細設計", "プログラム設計"]}
```

> sf-design-step1 はグループ確定・詳細設計の実行・必要に応じた連鎖呼び出し（step2/step3）を全て担う。コマンドは step1 の完了を待つだけでよい。

### 詳細設計が含まれず、プログラム設計が選択された場合（プログラム設計のみ または プログラム設計+機能一覧） → sf-design-step2 エージェント

```
プロジェクトフォルダパス: {project_dir}
output_dir: {output_dir}
author: {author}
project_name: {project_name}
version_increment: {version_increment}
target_group_ids: []
step0_3_done: false
```

> **パラメータ補足**:
> - `target_group_ids`: 対象グループIDリスト（list[str]）。空リストの場合 step2 内で AskUserQuestion により選択する。
> - `step0_3_done`: `true` なら step1 からの連鎖呼び出し（グループ→機能ID変換済み）、`false` なら単独実行（step2 内で Phase 0 から実施）。

### 機能一覧のみが選択された場合（詳細設計・プログラム設計が含まれない） → sf-design-step3 エージェント

```
プロジェクトフォルダパス: {project_dir}
output_dir: {output_dir}
author: {author}
project_name: {project_name}
version_increment: {version_increment}
```

---

## Step 2: 完了前クリーンアップ

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

## Step 3: 完了報告

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

⚠️ 要確認:
- {FG-XXX}: 生成失敗の概要（例: 関連オブジェクトが特定できなかった）
- 未分類コンポーネント {n} 件
（要確認事項がない場合はこのセクションごと省略）
```

---

## 注意事項

- 詳細設計は **グループ単位**（feature_groups.yml が必要）
- プログラム設計は **コンポーネント単位**（scan_features.py の出力が必要）
- 詳細設計を含む選択の場合は常に sf-design-step1 が先頭に立ち、連鎖的に後続エージェントを呼び出す
- コンポーネント名（API名・F-XXX）で対象を指定した場合は sf-design-step1 内でスクリプトにより FG-XXX に変換してから処理する
