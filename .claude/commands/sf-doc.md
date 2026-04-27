---
description: "Salesforceプロジェクトの基本設計資料（プロジェクト概要書・オブジェクト定義書）を会話形式で作成する。機能一覧・詳細設計・プログラム設計は /sf-design を使用。"
---

Salesforceプロジェクトの**基本設計資料（プロジェクト概要書・オブジェクト定義書）のみ**を会話形式で作成します。機能一覧・詳細設計・プログラム設計は `/sf-design` を使用してください。
スクリプトは `scripts/python/sf-doc-mcp/`（プロジェクトルートからの相対パス）にあります。

**AskUserQuestion のルール（厳守）:**
- **1質問1回答**: 複数の質問を1つの AskUserQuestion にまとめない。必ず1問ずつ順番に聞く
- **選択肢はデフォルト/スキップ値のみ**（**テキスト入力代替の single select でのみ適用**。multiSelect で資料/項目種別を列挙する場合は対象外）: AskUserQuestion には自動で「Other（自由入力）」が付く。choices に「Other」「自由入力」「手動入力」等の**そのままの語**を**絶対に含めない**。「スキップ」「デフォルト値を使う」等のみ記載する。**ただし schema 制約 ≥2 のため、前回値・自動取得値の対比として「別のフォルダを指定する」「別のエイリアスを使用」等の**コンテキスト具体ラベル**は許容**（Other 等価ではなく UX 上推奨。文言は対比対象を具体化すること）
- 選択肢がある場合（前回値・固定候補）は AskUserQuestion で提示する。テキスト自由入力が必要な場合（初回パス等）はチャットで直接聞く

**テンプレート置換ルール（厳守）:**
- Python インラインコード内、**および AskUserQuestion の label / description 内**の `{project_dir}` `{output_dir}` `{author}` `{last_author}` `{last_output_dir}` 等の `{...}` は f-string ではなく **Claude が実行前に実値でテキスト置換する** プレースホルダー。Bash / AskUserQuestion に渡す前に、値の種別に応じて以下の規則で置換する:
  - **パス値** (`{project_dir}` / `{output_dir}` 等): Windows パスの `\` はすべて `/` に置換し、末尾の `/` は除去する（例: `C:\work\` → `C:/work`）。raw string 末尾 `\` による SyntaxError を回避するため。`pathlib.Path` は Windows でも forward slash を正しく解釈する。
  - **任意文字列値** (`{author}` 等): シングルクォートで囲まれた箇所 (`'{author}'`) への埋め込み時は、値内の `'` を `\'` にエスケープし、改行 (`\n` `\r`) は空白に置換する（例: `O'Brien` → `O\'Brien`）。シェル引数 (`"{author}"`) への埋め込み時は値内の `"` を `\"` にエスケープする。
- 同じ規則は `.claude/agents/sf-doc-*.md` 等の連鎖エージェントでも適用される。委譲時に渡す値も上記規則で正規化済みの状態にすること。

---

## 前提: 情報源と依存関係

各資料が使う情報源と、最新化に必要なコマンド・選択肢。各エージェントの冒頭でも確認を促すが、事前に把握しておくこと。

| 資料 | 情報源 | 最新化コマンド |
|---|---|---|
| プロジェクト概要書 | `docs/overview/org-profile.md`<br>`docs/requirements/requirements.md`<br>`docs/architecture/system.json`<br>`docs/catalog/_data-model.md`<br>`docs/flow/swimlanes.json` | `/sf-memory` カテゴリ1・2 |
| オブジェクト定義書 | `docs/catalog/_index.md`（対象オブジェクト候補の選択のみ）<br>**Salesforce組織に直接接続**してフィールドメタデータを取得 | `/sf-memory` カテゴリ2 |

> **新規オブジェクト追加後**: `/sf-memory` カテゴリ2 を再実行 → _index.md に反映

**出力先**: 全ての資料は `{output_dir}/01_基本設計/` に統一して出力する（`output_dir` は Step 0-2 で指定）。

---

## Step 0: 資料種別の選択

AskUserQuestion で作成する資料を **multiSelect: true** で選択（**上流 → 下流** の順）:

- プロジェクト概要書 — プロジェクト概要書.xlsx
- オブジェクト定義書 — オブジェクト項目定義書.xlsx

選択結果を `selected_steps` として保持する（例: `["プロジェクト概要書"]` / `["オブジェクト定義書"]` / `["プロジェクト概要書", "オブジェクト定義書"]`）。

---

## Step 0-2: 共通情報の取得（資料種別選択後に一度だけ聞く）

> **前提**: このコマンドは Salesforce プロジェクトルート（`force-app/` があるフォルダ）をカレントディレクトリとして実行することを想定している。カレントディレクトリが不明な場合はチャットで確認すること。

まずカレントディレクトリを `project_dir` として確定する（以降の全スクリプト呼び出し・エージェント委譲で使用）:
```bash
python -c "import os; print(os.getcwd())"
```
出力されたパスを `{project_dir}` として保持する。

> **テキスト入力の必須ルール**: チャットでの入力を求めたら、ユーザーが返答するまで次の処理・質問には進まない。

### 前回設定の読み込み

```bash
python -c "
import pathlib, sys
try:
    import yaml
    p = pathlib.Path('docs/.sf/sf_doc_config.yml')
    if p.exists():
        d = yaml.safe_load(p.read_text(encoding='utf-8')) or {}
        print('author:' + str(d.get('author', '')))
        print('output_dir:' + str(d.get('output_dir', '')))
    else:
        print('author:')
        print('output_dir:')
except Exception as e:
    print('author:')
    print('output_dir:')
    print('warning: 前回設定の読み込みに失敗しました:', e, file=sys.stderr)
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
「スキップ」と返答された場合は空文字として扱う。結果を `{author}` として保持。

確定後、直ちに以下を実行して値を保持する（後続でコンテキスト汚染が起きても正確な値が残るようにするため）:
```bash
python -c "import pathlib; p=pathlib.Path('docs/.sf'); p.mkdir(parents=True, exist_ok=True); (p / '.author_tmp').write_text('{author}', encoding='utf-8')"
```

### 出力先フォルダ

**前回値がある場合:** AskUserQuestion で提示（2択+Other自動）:
- label: "前回: {last_output_dir}"、description: "前回と同じフォルダを使用"
- label: "別のフォルダを指定する"、description: "新しいパスをチャットで入力する"

「別のフォルダを指定する」または Other が選ばれた場合はチャットで入力してもらう。

**前回値がない場合:** チャットで直接聞く:
```
資料の出力先フォルダのパスを入力してください（このフォルダ内に 01_基本設計/ が作成されます）:
```

いずれの場合も、結果を `{output_dir}` として保持する（末尾のスラッシュは除去）。

確定後、直ちに以下を実行して値を保持する:
```bash
python -c "import pathlib; p=pathlib.Path('docs/.sf'); p.mkdir(parents=True, exist_ok=True); (p / '.output_dir_tmp').write_text(r'{output_dir}', encoding='utf-8')"
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
    p = pathlib.Path('docs/.sf/sf_doc_config.yml')
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

Step 0-2 完了後、`selected_steps` に応じて以下のエージェントを self-contained プロンプトで起動する。

| 選択 | 委譲先 | 備考 |
|---|---|---|
| プロジェクト概要書のみ | sf-doc-overview-writer | `pre_confirmed=false` で /sf-memory 最新化確認を実施 |
| オブジェクト定義書のみ | sf-doc-objects-writer | `selected_steps=["オブジェクト定義書"]` で単独モード |
| 両方選択 | sf-doc-objects-writer | `selected_steps=["プロジェクト概要書", "オブジェクト定義書"]`。内部で Phase 1 の一括確認後、sf-doc-overview-writer を `pre_confirmed=true` で連鎖呼び出し → objects 生成 |

> **両方選択時の呼び出し順序**: sf-doc-objects-writer が主役となり、Phase 1〜5 で全質問を終わらせた後、Phase 6 で sf-doc-overview-writer を `pre_confirmed=true` で呼ぶ。これにより「両方選択時は途中で確認が入らない」UX を保つ。

### プロジェクト概要書のみ → sf-doc-overview-writer

```
project_dir:    {project_dir}
output_dir:     {output_dir}
author:         {author}
pre_confirmed:  false
```

### オブジェクト定義書のみ → sf-doc-objects-writer

```
project_dir:    {project_dir}
output_dir:     {output_dir}
author:         {author}
selected_steps: ["オブジェクト定義書"]
```

### 両方選択 → sf-doc-objects-writer

```
project_dir:    {project_dir}
output_dir:     {output_dir}
author:         {author}
selected_steps: ["プロジェクト概要書", "オブジェクト定義書"]
```

---

## 完了報告

各エージェントの完了報告をそのまま出力する（コマンド側から追加のまとめ出力は行わない）。

- プロジェクト概要書のみ → sf-doc-overview-writer の完了報告を出力
- オブジェクト定義書のみ → sf-doc-objects-writer の完了報告を出力
- 両方選択 → sf-doc-objects-writer が概要書含む完了報告を行う（内部で sf-doc-overview-writer を連鎖呼び出し済み）
