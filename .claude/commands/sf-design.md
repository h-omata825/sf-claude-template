---
description: "Salesforce 設計書（詳細設計・プログラム設計・機能一覧）を生成する。詳細設計/プログラム設計/機能一覧の3種別をマルチセレクトで選択して実行。"
---

Salesforce プロジェクトの設計書を生成します。

**詳細設計 / プログラム設計** の2層構成に対応しています。

**AskUserQuestion のルール（厳守）:**
- **1質問1回答**: 複数の質問を1つの AskUserQuestion にまとめない。必ず1問ずつ順番に聞く
- **選択肢はデフォルト/スキップ値のみ**（**テキスト入力代替の single select でのみ適用**。multiSelect で資料/項目種別を列挙する場合は対象外）: AskUserQuestion には自動で「Other（自由入力）」が付く。choices に Other・「自由入力」・「手動入力」等の選択肢を**絶対に含めない**。「スキップ」「デフォルト値を使う」等のみ記載する
- 選択肢がある場合（前回値・固定候補）は AskUserQuestion で提示する。テキスト自由入力が必要な場合（初回パス等）はチャットで直接聞く

**テンプレート置換ルール（厳守）:**
- Python インラインコード内、**および AskUserQuestion の label / description 内**の `{project_dir}` `{output_dir}` `{author}` `{last_author}` `{last_output_dir}` `{version_increment}` 等の `{...}` は f-string ではなく **Claude が実行前に実値でテキスト置換する** プレースホルダー。Bash / AskUserQuestion に渡す前に、値の種別に応じて以下の規則で置換する:
  - **パス値** (`{project_dir}` / `{output_dir}` 等): Windows パスの `\` はすべて `/` に置換し、末尾の `/` は除去する（例: `C:\work\` → `C:/work`）。raw string 末尾 `\` による SyntaxError を回避するため。`pathlib.Path` は Windows でも forward slash を正しく解釈する。
  - **任意文字列値** (`{author}` 等): シングルクォートで囲まれた箇所 (`'{author}'`) への埋め込み時は、値内の `'` を `\'` にエスケープする（例: `O'Brien` → `O\'Brien`）。
  - **列挙値** (`{version_increment}`): `minor` / `major` 以外が指定された場合は `minor` にフォールバックし、ユーザーに「未知の値のためminorに置換」と警告する。
- 同じ規則は `.claude/agents/sf-design-step*.md` 等の連鎖エージェントでも適用される。委譲時に渡す値も上記規則で正規化済みの状態にすること。

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

選択の組み合わせとディスパッチ先:

| 選択 | 委譲先 | 備考 |
|---|---|---|
| 詳細設計のみ | sf-design-step1 | step1 内でグループ選択 |
| プログラム設計のみ | sf-design-step2 | step2 内でグループ選択・SF_ALIAS 取得 |
| 機能一覧のみ | sf-design-step3 | — |
| 詳細+プログラム設計 | sf-design-step1 | step1 内でグループ一括確定 → step2 を連鎖呼び出し |
| 詳細設計+機能一覧 | sf-design-step1 | step1 が詳細設計完了後 step3 を連鎖呼び出し |
| プログラム設計+機能一覧 | sf-design-step2 | step2 内で機能一覧も生成（step3 は不要） |
| 詳細+プログラム+機能一覧 | sf-design-step1 | step1 → step2（機能一覧も生成）の順に連鎖 |

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

**前回値がない場合:** チャットで直接聞く:
```
作成者名を入力してください（不要な場合は「スキップ」と返答）:
```
「スキップ」と返答された場合は空文字として扱う。

確定後、直ちに以下を実行して値を保持する（後続でコンテキスト汚染が起きても正確な値が残るようにするため）:
```bash
python -c "import pathlib; p = pathlib.Path('docs/.sf'); p.mkdir(parents=True, exist_ok=True); p.joinpath('.author_tmp').write_text('{author}', encoding='utf-8')"
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
python -c "import pathlib; p = pathlib.Path('docs/.sf'); p.mkdir(parents=True, exist_ok=True); p.joinpath('.output_dir_tmp').write_text(r'{output_dir}', encoding='utf-8')"
```

### バージョン種別

AskUserQuestion で選択する（2択＋Other自動）:
- label: "minor"、description: "機能追加・仕様変更・軽微な修正（デフォルト）"
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

### 設定の保存

確定した値を保存する（次回のデフォルト値として使用）:
```bash
python -c "
import pathlib, sys
author_f = pathlib.Path('docs/.sf/.author_tmp')
outdir_f = pathlib.Path('docs/.sf/.output_dir_tmp')
try:
    import yaml
    author = author_f.read_text(encoding='utf-8').strip() if author_f.exists() else ''
    output_dir = outdir_f.read_text(encoding='utf-8').strip() if outdir_f.exists() else ''
    p = pathlib.Path('docs/.sf/sf_design_config.yml')
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.dump({'author': author, 'output_dir': output_dir}, allow_unicode=True, default_flow_style=False), encoding='utf-8')
except Exception as e:
    print('設定の保存に失敗:', e, file=sys.stderr)
    sys.exit(1)
finally:
    # 成功・失敗にかかわらず一時ファイルは必ず削除する
    for f in [author_f, outdir_f]:
        f.unlink(missing_ok=True)
"
```

---

## ディスパッチ: 各エージェントへの委譲

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

### 詳細設計が含まれず、プログラム設計のみ選択された場合 → sf-design-step2 エージェント

```
プロジェクトフォルダパス: {project_dir}
output_dir: {output_dir}
author: {author}
project_name: {project_name}
version_increment: {version_increment}
target_group_ids: ""
step0_3_done: false
```

> **パラメータ補足**:
> - `target_group_ids`: 対象グループIDリスト（カンマ区切り文字列）。空文字の場合 step2 内で AskUserQuestion により選択する。
> - `step0_3_done`: `true` なら step1 からの連鎖呼び出し（グループ→機能ID変換済み）、`false` なら単独実行（step2 内で Phase 0 から実施）。

### 機能一覧のみ選択された場合 → sf-design-step3 エージェント

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
for subdir in ['01_基本設計', '02_詳細設計', '03_プログラム設計']:
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
