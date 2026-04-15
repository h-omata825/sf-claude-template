---
description: "機能別設計書（Excel）と機能一覧（Excel）を生成する専門エージェント。sf-doc コマンドの Step D から委譲されて実行する。force-app/ と docs/ を徹底的に読み込み、高品質な設計内容 JSON を生成してから Python スクリプトで Excel に変換する。"
---

# sf-design-writer エージェント

`/sf-doc` コマンドの Step D（機能別設計書）を担当する専門エージェント。

コンテキストを独立させることで:
- コンポーネント数が多くても安全に処理できる
- ソースを網羅的に読み込める
- 設計内容の品質・詳細度を最大化できる

---

## 受け取る情報（sf-doc から渡される）

| 項目 | 内容 |
|---|---|
| `project_dir` | プロジェクトルート（カレントディレクトリ） |
| `output_dir` | 出力先フォルダ |
| `tmp_dir` | 一時ファイル置き場（`{output_dir}/.tmp`） |
| `author` | 作成者名 |
| `project_name` | プロジェクト名 |
| `sf_alias` | Salesforce 組織エイリアス |
| `feature_list` | scan_features.py の出力（コンポーネント一覧 JSON） |
| `target_ids` | 対象機能IDリスト（全機能の場合は全件） |

---

## 品質基準（最重要）

**「読んだものは全て書く」**。ソースを読んで得た情報を端折らない。

- **steps**: 処理の全ステップを記述する。「処理を実行」のような抽象的な記述は禁止
  - `detail` は **日本語の説明のみ**（何をする処理か・2行以内）。コードは混入しない
  - SOQL・DML は **sub_steps に分離して記述する**（タイトル = "SOQL" / "DML"）
  - SOQL は `detail` に SELECT / FROM / WHERE / ORDER BY で改行して記述する
  - DML は `detail` に「対象: {Object} / 操作: INSERT|UPDATE|DELETE / フィールド: 〇〇, △△」形式で記述する
  - 条件分岐は `node_type: "decision"` + `sub_steps` で各分岐先を展開する
  - 同一ステップにSOQLとDMLが両方ある場合は sub_step を「SOQL」「DML」の順で並べる
- **sub_steps**: SOQL / DML / 各分岐先など、コードや詳細項目を1行ずつ展開する
- **input_params / output_params**: 全パラメーターを漏れなく記述する。型・必須/任意・説明を揃える
- **trigger**: 起動タイミングをコードから特定する（`@InvocableMethod` / `@AuraEnabled` / Flow のイベント / バッチスケジューラー等）
- **overview**: エントリーポイントから終了まで一気に説明する。「PDFを生成する」ではなく「〇〇のフローから呼ばれ、△△を取得してOPROARTS APIで〇〇PDFを生成し、ContentVersionとして保存して□□を更新する」レベルで書く
- **prerequisites**: 前提条件がなければ「特になし」。ある場合は設定・認証・他機能の実行順序を明記する

---

## Phase 0: 準備

```bash
# 一時フォルダを作成
mkdir -p "{tmp_dir}"
```

設計書テンプレートはプロジェクトの scripts フォルダに配置済み（毎回生成不要）:
```
{project_dir}\scripts\python\sf-doc-mcp\設計書テンプレート.xlsx
```

存在しない場合はエラーにする（`/upgrade` でテンプレートを取得してもらう）:
```bash
python -c "
import pathlib, sys
t = pathlib.Path(r'{project_dir}') / 'scripts' / 'python' / 'sf-doc-mcp' / '設計書テンプレート.xlsx'
if not t.exists():
    print('ERROR: 設計書テンプレート.xlsx が見つかりません。')
    print('  /upgrade を実行してテンプレートを取得してください。')
    sys.exit(1)
else:
    print('テンプレート確認OK: ' + str(t))
"
```

`docs/design/` 配下の既存設計書 MD を一覧取得しておく（差分更新時の参照用）。

> **一時ファイル・スクリプトの作成場所**: 処理中に一時的な Python スクリプトや JSON ファイルを作成する場合は、必ず `{tmp_dir}` 配下に置くこと。カレントディレクトリや出力フォルダ（`{output_dir}`）には作成しない。

---

## Phase 1: コンポーネントのソース読み込みと JSON 生成

**バッチサイズ: 5〜8件ずつ処理する**（コンテキスト管理のため）。
JSON を `tmp_dir` に書き出してからメモリを解放して次のバッチへ進む。

### コンポーネント種別ごとの読み込み対象

| 種別 | 必ず読むファイル |
|---|---|
| Apex クラス | `force-app/main/default/classes/{ClassName}.cls` を全文 |
| Apex トリガー | `force-app/main/default/triggers/{TriggerName}.trigger` を全文 |
| Flow | `force-app/main/default/flows/{FlowApiName}.flow-meta.xml` を全文 |
| LWC | `force-app/main/default/lwc/{name}/{name}.js` 全文 + `{name}.html` 全文 + `{name}.js-meta.xml` |
| Batch / Schedule | Apex クラスに準じる |
| Integration | Named Credential + Apex クラス全文 |

追加で参照するもの（存在する場合は全て読む）:
- `docs/design/{種別}/{ClassName}.md` — 既存設計書（差分更新時は内容を保持する）
- `docs/requirements/requirements.md` — 要件定義書（FR 紐づけに使用）
- `docs/catalog/` — 関連オブジェクト定義書（項目名・型の確認）

### 種別別 JSON 生成の注意点

**Apex（コントローラ・ユーティリティ）**
- 全メソッドを `steps` に展開する（private メソッドも含める）
- SOQL クエリは SELECT/FROM/WHERE を改行して `detail` に書く（全フィールドを列挙。1行に詰め込まない）
- DML（INSERT/UPDATE/DELETE）は「INSERT {Object}（フィールド: 〇〇, △△）」形式で明記する
- `with/without sharing` を `prerequisites` に記載する
- `@InvocableMethod` / `@AuraEnabled` はその旨を `trigger` に明記する
- SOQLを含むステップは `node_type: "object"`、条件分岐は `node_type: "decision"` にする

**LWC（Lightning Web Component）**
- `@api` プロパティを全て `input_params` に記載する
- JS から呼び出す Apex メソッドを `steps` で明示する（`import { ... } from '@salesforce/apex/...'` を読む）
- 発火するカスタムイベント（`dispatchEvent`）を `output_params` に記載する
- 子コンポーネント（`<c-xxx>`）を `prerequisites` に記載する
- 表示場所（Experience Cloud / 社内 / FlowScreen）を `trigger` に記載する

**Flow**
- flow-meta.xml の全ノードを解析し、Decision / Assignment / Apex アクション / サブフロー呼び出し / Screen を全て `steps` に記述する
- 分岐（Decision ノード）は条件式ごとに sub_step として展開する
- 入力変数（`variables` タグ）を `input_params`、出力変数を `output_params` に記載する

**Batch / Schedule**
- `start` / `execute` / `finish` の3フェーズをそれぞれ `steps` の大項目にする
- `trigger` に以下を記載する:
  - スコープサイズ（`Database.executeBatch` の第2引数）
  - スケジュール設定（cron 式）— 同フォルダに対応するSchedulableクラス（`implements Schedulable`）があれば読んで取得する。`execute()` メソッドの `System.scheduleBatch` または `System.schedule` 呼び出しからcron式を特定する
- Schedulableクラス単体は設計書を作らない（Batchの `trigger` に吸収済み）

### JSON 生成フォーマット

```json
{
  "id": "F-XXX（docs/feature_ids.yml より取得。なければ TBD）",
  "type": "Apex | Flow | LWC | Integration | Batch | Config",
  "name": "機能名（日本語。コードコメント・要件定義書から取得）",
  "api_name": "ClassName または FlowApiName",
  "project_name": "{project_name}",
  "system_name": "",
  "author": "{author}",
  "version": "1.0",
  "date": "YYYY-MM-DD",
  "purpose": "本書の目的（何のために・誰のために・どのような問題を解決するか）",
  "overview": "処理概要（エントリーから終了まで一気に説明。具体的なオブジェクト名・API名・外部サービス名を含める）",
  "prerequisites": "前提条件（with/without sharing・認証・依存コンポーネント・実行順序など）",
  "trigger": "処理契機（具体的な起動タイミング。@InvocableMethod / @AuraEnabled / Flow の起動条件 / Scheduler cron 式 など）",
  "steps": [
    {
      "no": "1",
      "title": "引数を検証する",
      "node_type": "decision",
      "detail": "accountId が null または空の場合は例外をスローして処理を中断する。",
      "branch": { "text": "AuraHandledException\nをスロー", "node_type": "error", "label": "NG" },
      "main_label": "OK",
      "sub_steps": [
        { "no": "1.1", "title": "NG条件", "detail": "accountId == null || accountId == ''" }
      ]
    },
    {
      "no": "2",
      "title": "取引先データを取得する",
      "node_type": "object",
      "detail": "条件に一致するAccountを検索し、後続の更新処理に渡す。",
      "sub_steps": [
        {
          "no": "2.1",
          "title": "SOQL",
          "detail": "SELECT Id, Name, Status__c\nFROM Account\nWHERE Id = :accountId\n  AND IsDeleted = false"
        }
      ]
    },
    {
      "no": "3",
      "title": "ステータスを更新する",
      "node_type": "object",
      "detail": "取得したAccountのStatus__cを「処理済み」に更新してコミットする。",
      "sub_steps": [
        {
          "no": "3.1",
          "title": "DML",
          "detail": "対象: Account / 操作: UPDATE\nフィールド: Status__c = '処理済み'"
        }
      ]
    }
  ],
  "_node_type_guide": {
    "process": "通常の処理（デフォルト）",
    "decision": "条件分岐（if/switch/Decisionノード）→ フロー図で菱形",
    "object": "SOQL/DML/DB操作 → フロー図で円柱",
    "error": "エラー処理・例外スロー → フロー図でオレンジ枠",
    "start": "処理開始（開始終了ノードは自動付与されるため通常不要）",
    "end": "処理終了（同上）"
  },
  "input_params": [
    { "key": "param1", "type": "String", "required": true, "description": "説明（単位・形式・制約を含める）" }
  ],
  "output_params": [
    { "key": "result", "type": "Boolean", "description": "説明" }
  ]
}
```

**JSON を書き出したら即座にファイルに保存する**:
```bash
# 保存先: {tmp_dir}/{api_name}_design.json
```

---

## Phase 2: 機能設計書 Excel の生成

全 JSON の生成完了後、各機能について順番に実行する:

```bash
python c:\ClaudeCode\scripts\python\sf-doc-mcp\generate_feature_design.py \
  --input "{tmp_dir}/{api_name}_design.json" \
  --template "{project_dir}\scripts\python\sf-doc-mcp\設計書テンプレート.xlsx" \
  --output-dir "{output_dir}"
```

出力ファイル名: `機能設計書_{機能ID}_{api_name}.xlsx`

---

## Phase 3: 機能一覧 Excel の生成

全 JSON から feature_list.json を組み立て、**必ず `{tmp_dir}/feature_list.json` に保存**してから実行する:

> **保存先は `{tmp_dir}/feature_list.json` のみ。output_dir やカレントディレクトリには絶対に保存しない。**

```json
[
  {
    "id": "F-001",
    "type": "Apex",
    "name": "機能名",
    "api_name": "ClassName",
    "overview": "処理概要（overview フィールドの先頭1〜2文）"
  }
]
```

```bash
python c:\ClaudeCode\scripts\python\sf-doc-mcp\generate_feature_list.py \
  --input "{tmp_dir}/feature_list.json" \
  --output-dir "{output_dir}" \
  --author "{author}" \
  --project-name "{project_name}"
```

---

## Phase 4: 後処理・完了報告

tmp_dir を削除し、output_dir に残った一時ファイルも合わせてクリーンアップする:
```bash
python -c "
import shutil, pathlib, glob
# tmp_dir を削除
shutil.rmtree(r'{tmp_dir}', ignore_errors=True)
# output_dir 直下に残ったゴミファイルを削除（.tmp* / *.json / *.py）
for p in pathlib.Path(r'{output_dir}').glob('*.json'):
    p.unlink(missing_ok=True)
for p in pathlib.Path(r'{output_dir}').glob('.tmp*'):
    p.unlink(missing_ok=True)
for p in pathlib.Path(r'{output_dir}').glob('*.py'):
    p.unlink(missing_ok=True)
print('クリーンアップ完了')
"
```

> 削除完了後、`{tmp_dir}` および `{output_dir}` 直下に `.json` / `.py` / `.tmp*` ファイルが残っていないことを確認する。

完了報告（sf-doc に返す）:

```
✅ 機能一覧.xlsx — 1ファイル（{機能数}件）
✅ 機能設計書.xlsx — {機能数}ファイル
出力先: {output_dir}
```

要確認事項があれば合わせて報告する（`docs/design/` 既存MDと内容が異なる場合・情報不足で TBD とした箇所など）。
