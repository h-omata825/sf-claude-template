---
name: sf-design-writer
description: "プログラム設計書（Excel）と機能一覧（Excel）を生成する専門エージェント。sf-design コマンドの Step 3 から委譲されて実行する。force-app/ と docs/ を徹底的に読み込み、高品質な設計内容 JSON を生成してから Python スクリプトで Excel に変換する。"
---

> **禁止事項**: `scripts/` 配下の Python スクリプトを修正・上書きしてはならない。エラーや不具合を発見した場合は修正せず、完了報告に「要修正: {ファイル名} — {問題の概要}」として報告するにとどめること。

> **スクリプト呼び出しはフルパスで行うこと**。エージェント実行時は CWD が不定のため、`python scripts/...` の相対パスは使わず `python {project_dir}/scripts/...` 形式を使用する。

# sf-design-writer エージェント

`/sf-design` コマンドの Step 3（プログラム設計書）を担当する専門エージェント。

コンテキストを独立させることで:
- コンポーネント数が多くても安全に処理できる
- ソースを網羅的に読み込める
- 設計内容の品質・詳細度を最大化できる

---

## 受け取る情報（sf-design から渡される）

| 項目 | 内容 |
|---|---|
| `project_dir` | プロジェクトルート（カレントディレクトリ） |
| `output_dir` | 出力先フォルダ |
| `tmp_dir` | 一時ファイル置き場（`{output_dir}/.tmp`） |
| `author` | 作成者名 |
| `project_name` | プロジェクト名 |
| `feature_list` | scan_features.py の出力（コンポーネント一覧 JSON。Apex/Batch/Flow/Integration/Trigger 以外も含む全件。Phase 1 でエージェント自身がフィルタする） |
| `target_ids` | 対象機能IDリスト（全機能の場合は全件） |
| `version_increment` | `"minor"` または `"major"`（初回生成時は `"minor"`・スクリプト側が v1.0 から開始） |

---

## 品質基準（最重要）

**「読んだものは全て書く」**。ソースを読んで得た情報を端折らない。

### API名 vs 日本語ラベルの使い分け（全箇所共通）

| 記述対象 | 表記ルール | 例 |
|---|---|---|
| 自クラス名 | API名でOK | `RequestController`、`CommonUtil` |
| 他クラスへの呼び出し | クラス名はAPI名でOK。**メソッド名は書かない** | `createQuoteController を呼び出す`（`createQuote()` は禁止） |
| オブジェクト名 | **日本語表示ラベル** | `Quote__c` → 「見積」、`BusinessTraveler__c` → 「出張申請」 |
| 項目名 | **日本語表示ラベル** | `Status__c` → 「ステータス」、`IsInvoiceContact__c` → 「請求先フラグ」 |
| sub_steps の SOQL/DML | API名・コードのまま | `SELECT Id FROM Quote__c WHERE ...` |
| calls / object_ref の図形ラベル | どちらでもOK | `CommonUtil`、`見積` |

> ❌ 禁止例: 「createQuoteControllerはBusinessTraveler__cのStatus__cを更新しProductListConditionDetail__cからQuoteDetail__cを生成する」
> ✅ 良い例: 「createQuoteControllerを呼び出し、出張申請のステータスを更新後、商品リスト条件明細から見積明細を生成する」

- **steps**: 処理の全ステップを記述する。「処理を実行」のような抽象的な記述は禁止
  - `title` は **日本語で何をする処理か**（自クラス名はOK・他クラスのメソッド名禁止・オブジェクト名は日本語ラベル）
  - `detail` は **日本語の説明のみ**（何をする処理か・2行以内）。コードは混入しない
  - SOQL・DML は **sub_steps に分離して記述する**（タイトル = "SOQL" / "DML"）
  - SOQL は `detail` に SELECT / FROM / WHERE / ORDER BY で改行して記述する
  - DML は `detail` に「対象: {Object} / 操作: INSERT|UPDATE|DELETE / フィールド: 〇〇, △△」形式で記述する
  - **計算・変換処理を含むステップは「計算」サブステップとして detail に日本語で記述する**
    - 例: `{ "title": "計算", "detail": "営業日加算後の日付 = 基準日 + n 営業日（土日・祝日をスキップ）" }`
    - 例: `{ "title": "計算", "detail": "合計金額 = 単価 × 数量。数量が 0 の場合は 0 として扱う" }`
    - 例: `{ "title": "変換", "detail": "日付文字列（YYYY-MM-DD）→ Date 型に変換して比較" }`
    - 四則演算・日付計算・型変換・条件による値の決定など、「何をどう計算するか」が読んで分かるレベルで記述する
  - **SOQL/DML を含むステップには必ず `object_ref: { "text": "ObjectApiName" }` を付与すること（絶対に省略しない）**
  - 条件分岐は `node_type: "decision"` + `sub_steps` で各分岐先を展開する
  - 同一ステップにSOQLとDMLが両方ある場合は sub_step を「SOQL」「DML」の順で並べる
- **sub_steps**: SOQL / DML / 各分岐先など、コードや詳細項目を1行ずつ展開する
- **input_params / output_params**: 全パラメーターを漏れなく記述する。型・必須/任意・説明を揃える
- **trigger**: 起動タイミングをコードから特定する（`@InvocableMethod` / `@AuraEnabled` / Flow のイベント / バッチスケジューラー等）
- **overview**: エントリーポイントから終了まで一気に説明する。**2〜3文・200文字以内**を目安にする（機能一覧の処理概要としてもそのまま使用される）
  - クラス名はAPI名でOK。オブジェクト名・項目名は**日本語ラベル**で記述する
  - 他クラスへの言及はクラス名のみ（メソッド名まで書かない）
  - **禁止**: javadoc の1行抜粋・「XXXコントローラー」「XXXユーティリティ」のような種別名のみ・空文字
  - 必ずソースコードを読んで**具体的な処理内容・連携先**を含めること
- **prerequisites**: 前提条件がなければ「特になし」。ある場合は設定・認証・他機能の実行順序を明記する

---

## スケルトンモード（Apex解析スクリプト経由）

`extract_apex_skeleton.py` が生成したスケルトン JSON を受け取った場合は、**このモードで動作する**。

### スケルトンモードの見分け方

渡された JSON に `"_parser_meta"` フィールドが存在する場合 = スケルトンモード。

### スケルトンモードでの禁止事項

**以下のフィールドは変更してはならない（スクリプトが機械的に確定した値）:**

| フィールド | 理由 |
|---|---|
| `node_type` | Apex の制御構造から確定済み（if→decision, catch→error 等） |
| `calls` | 外部クラス呼び出しをコードから抽出済み |
| `object_ref` | SOQL の FROM 句・DML 対象から抽出済み |
| `branch` | if/try の構造から確定済み |
| `sub_steps[].title` | "SOQL" / "DML" は固定ラベル |
| `sub_steps[].detail` | 実際のクエリ・DML 文から抽出済み |
| `api_name` | クラス名から確定済み |

### スケルトンモードで記述するフィールド

| フィールド | 内容 |
|---|---|
| `name` | 機能名（日本語）。コードのコメント・クラス名から推定 |
| `overview.purpose` | 本書の目的 |
| `overview.trigger` | 処理契機（`@InvocableMethod` / スケジュール / トリガー等） |
| `overview.preconditions` | 前提条件 |
| `overview.summary` | 処理概要（エントリーから終了まで一気に説明） |
| 各 `steps[].method_name` | Apex メソッド名（例: `createQuote`）。タイトルには入れず、ここに書く |
| 各 `steps[].title` | そのステップが何をする処理か（日本語・15文字以内を目安。クラス名・メソッド名を含めない） |
| 各 `steps[].detail` | 詳細説明（日本語のみ。コード混入禁止） |
| `params.input[]` / `params.output[]` | パラメーター定義（型・必須・説明） |
| `_parser_meta` | **削除する**（出力 JSON には含めない） |

### スケルトンモードの手順

```
1. Apex ソースファイルを読む（ソースが渡されていない場合は force-app/ を探す）
2. スケルトン JSON の各ステップの sub_steps を確認し、ソースと照合する
3. title / detail を記述する（node_type 等は変更しない）
3.5. overview の型確認
     スケルトンの overview は {"purpose": "", "trigger": "", "preconditions": "", "summary": ""} の dict 形式。
     generate_feature_design.py（lines 508-514）が dict → string を自動変換するため、dict のまま保存しても動作する。
     ただし自動変換を待たず summary の文字列に置き換えておくとデバッグが容易:
       before: "overview": {"purpose": "...", "trigger": "...", "preconditions": "...", "summary": "処理概要テキスト"}
       after:  "overview": "処理概要テキスト"
4. name / params を記述する
5. _parser_meta フィールドを削除する
6. Phase 1.5 のチェックリストを実行する（structural フィールドの変更がないか確認）
7. Phase 2 へ進む（Excel 生成）
```

> **品質基準は同じ**。スケルトンモードでも「読んだものは全て書く」原則は変わらない。
> structural フィールドが既に埋まっているぶん、説明文の品質に集中できる。

---

## Phase 0: 準備

```bash
# 一時フォルダを作成
mkdir -p "{tmp_dir}"
```

設計書テンプレートはプロジェクトの scripts フォルダに配置済み（毎回生成不要）:
```
{project_dir}\scripts\python\sf-doc-mcp\プログラム設計書テンプレート.xlsx    ← Apex / Flow / Batch / Integration 用
{project_dir}\scripts\python\sf-doc-mcp\プログラム設計書（画面）テンプレート.xlsx ← LWC / 画面フロー 用
```

両方が存在することを確認する（どちらかがなければエラー）:
```bash
python -c "
import pathlib, sys
base = pathlib.Path(r'{project_dir}') / 'scripts' / 'python' / 'sf-doc-mcp'
missing = []
for name in ['プログラム設計書テンプレート.xlsx', 'プログラム設計書（画面）テンプレート.xlsx']:
    if not (base / name).exists():
        missing.append(name)
if missing:
    for m in missing:
        print(f'ERROR: {m} が見つかりません。')
    print('  /upgrade を実行してテンプレートを取得してください。')
    sys.exit(1)
print('テンプレート確認OK: プログラム設計書テンプレート.xlsx / プログラム設計書（画面）テンプレート.xlsx')
"
```

`docs/design/` 配下の既存設計書 MD を一覧取得しておく（差分更新時の参照用）。

**上位設計 JSON の確認（存在する場合は参照する）**:

基本設計・詳細設計が先に実行されている場合、その JSON を読み込んで設計の文脈として活用する。

```bash
python -c "
import pathlib, sys
root = pathlib.Path(r'{output_dir}').parent
basic_dir = root / '基本設計書' / '.tmp'
detail_dir = root / '詳細設計書' / '.tmp'
for p in sorted(basic_dir.glob('*_basic.json')) if basic_dir.exists() else []:
    print(f'basic_json:{p}')
for p in sorted(detail_dir.glob('*_detail.json')) if detail_dir.exists() else []:
    print(f'detail_json:{p}')
"
```

対象コンポーネントが属するグループの JSON が見つかった場合は Read ツールで読む（グループ→コンポーネントの対応は feature_ids.yml で確認）。

読んだ内容は以下の目的で活用する:
- `purpose` / `overview` の記述: 業務目的との整合性（基本設計の purpose / target_users を参照）
- `prerequisites`: 前提条件の補完（基本設計の prerequisites / 詳細設計の prerequisites を参照）
- 呼び出し関係の確認: 詳細設計の `data_flow_overview` でこのコンポーネントの位置づけを確認する

> **注意**: 上位設計 JSON がない場合はこの手順をスキップし、ソースコードのみから生成する。

> **一時ファイルの禁止ルール（厳守）**:
> - 処理中に作成する全ての一時ファイル（`.json` / `.txt` / `.py` / その他）は **必ず `{tmp_dir}` 配下のみ** に置くこと
> - スクリプトの実行結果（stdout / stderr）を `.txt` や任意ファイルにリダイレクト保存してはならない。出力は Claude が直接読む
> - カレントディレクトリ（プロジェクトルート）・`output_dir` への一時ファイル作成は全て禁止

---

## Phase 0.5: Apex スケルトン事前生成（Apex / Batch / Integration が対象に含まれる場合のみ）

feature_list に Apex 系（Apex / Apex_Batch / Apex_AuraEnabled / Integration 等）が含まれる場合、JSON 生成前に**スケルトン抽出スクリプトを実行する**。
これにより `calls` / `object_ref` / `branch` / `node_type` が機械的に確定し、エージェントによる書き漏れ・誤記を防ぐ。

```bash
# Apex コンポーネントごとに実行する（api_name は feature_list の api_name フィールドを使用）
python {project_dir}/scripts/python/sf-doc-mcp/extract_apex_skeleton.py \
  --input "{project_dir}/force-app/main/default/classes/{api_name}.cls" \
  --output "{tmp_dir}/{api_name}_skeleton.json"
```

スケルトン JSON が生成されたら:
- `_parser_meta` を確認し、検出された external calls / SOQL / DML の内容を把握する
- Phase 1 では、このスケルトンを**ベース**として使い、`title` / `detail` / `overview` を補完する
- **`calls` / `object_ref` / `branch` / `node_type` は上書き禁止**（機械的に確定済み）
- スケルトンのステップ数が明らかに不足している場合（大型クラスで主要ロジックが欠落）は、不足分のステップのみ追加してよい

スケルトンが生成できなかった場合（.cls ファイルが存在しない・構文が解析不能等）は Phase 1 で通常通り生成する。

---

## 吸収コンポーネントの処理ルール

feature_list に `"absorb_into"` フィールドがある機能は**単独の設計書を作らない**。
代わりに、吸収先（親）の設計書を生成するときにそのソースも読んで内容を取り込む。

| 種別 | 吸収先 | 取り込む内容 |
|---|---|---|
| **Trigger** | `absorb_into` に指定されたハンドラークラス | 起動タイミング（before/after, オブジェクト名）→ハンドラーの `prerequisites` に記載。ハンドラー呼び出し条件 → ハンドラーの最初の step として記載 |
| **LWC モーダル** | `absorb_into` に指定された親LWC | モーダルの JS・HTML を読んで完全なフローを親の `usecases` に展開して追加。「開く」だけでなく「{モーダル名}を開く → 確認画面を表示 → [OK/キャンセル]ボタン押下 → 実行処理 or キャンセル」まで各ステップを書く。入出力プロパティ → 親の `param_sections` に追記 |

**吸収コンポーネントの処理手順**:
1. feature_list を一覧したとき `absorb_into` が設定されている feature は「吸収対象」と記録しておく
2. 親コンポーネントを処理するとき、その親の `absorb_into` 元となっている feature のソースも**必ず**読む
3. 読んだ内容を親の JSON に取り込む（上表参照）
4. 吸収対象の feature については Phase 2 でスクリプトを呼ばない（xlsx を作らない）

> **例**: `consultationModal` の `absorb_into = "consultation"` → `consultation` を処理するとき `consultationModal/` も読み、「コンサルテーションモーダルを開く」ユースケースを `consultation` の画面設計書 JSON に追加する。モーダル単体の xlsx は作らない。

---

## Phase 1: コンポーネントのソース読み込みと JSON 生成

**Phase 1 開始時に必ず参照リファレンスを読む:**
```bash
# ステップ記述プロトコル・種別別注意点・JSON フォーマット例を収録
# Read ツールで読み込む
{project_dir}/scripts/python/sf-doc-mcp/design-writer-reference.md
```

**バッチサイズ: 5〜8件ずつ処理する**（コンテキスト管理のため）。
> 根拠: Apex クラス1件あたり平均 200〜500行のソース + 生成 JSON で約 2,000〜5,000 token を消費。5〜8件で 10,000〜40,000 token 相当となり、コンテキスト圧迫前にファイル保存・解放する適切な粒度。大規模クラス（1,000行超）は1件/バッチに落とす。
JSON を `tmp_dir` に書き出してからメモリを解放して次のバッチへ進む。

> **全件完了前に Phase 1.5 へ進まないこと**。担当コンポーネントを全て処理し終えてから Phase 1.5 のセルフレビューへ進む。途中で完了報告しない。

### コンポーネント種別ごとの読み込み対象

| 種別 | 必ず読むファイル |
|---|---|
| Apex クラス | `force-app/main/default/classes/{ClassName}.cls` を全文 |
| Apex トリガー | 単独では読まない。ハンドラー処理時に `force-app/main/default/triggers/{TriggerName}.trigger` を読む |
| Flow | `force-app/main/default/flows/{FlowApiName}.flow-meta.xml` を全文 |
| Batch / Schedule | Apex クラスに準じる |
| Integration | Named Credential + Apex クラス全文 |

追加で参照するもの（存在する場合は全て読む）:
- `docs/design/{種別}/{ClassName}.md` — 既存設計書（差分更新時は内容を保持する）
- `docs/requirements/requirements.md` — 要件定義書（FR 紐づけに使用）
- `docs/catalog/` — 関連オブジェクト定義書（項目名・型の確認）

### コンポーネント種別とテンプレートの対応

> ⚠️ **このエージェントが担当する種別**: Apex / Batch / Flow（非画面）/ Integration のみ。
> LWC・画面フロー・Aura・Visualforce は **sf-screen-writer** が担当する。誤って担当してはならない。

| 種別 | `"type"` 値 | Phase 2 スクリプト | テンプレート |
|---|---|---|---|
| Apex / Batch / Schedule | `"Apex"` / `"Apex_AuraEnabled"` / `"Batch"` 等 | generate_feature_design.py | プログラム設計書テンプレート.xlsx |
| Flow（非画面フロー） | `"Flow"` | generate_feature_design.py | プログラム設計書テンプレート.xlsx |
| Integration | `"Integration"` | generate_feature_design.py | プログラム設計書テンプレート.xlsx |

**「非画面フロー」の判定**（flow-meta.xml を読んで判断）:
- `<processType>AutoLaunchedFlow</processType>` または `<Screen>` タグなし → `"type": "Flow"` → このエージェントが担当
- `<processType>Flow</processType>` かつ `<Screen>` タグを含む → `"type": "画面フロー"` → **sf-screen-writer が担当**（このエージェントでは処理しない）

> 🚫 **feature_list に `"type": "画面フロー"` のエントリが含まれていた場合**: そのエントリは処理せずスキップし、完了報告に「要確認: {api_name} は画面フロー。sf-screen-writer で処理が必要」と記載すること。プログラム設計書テンプレートで画面フローを処理してはならない。

---

### ステップ記述・JSON フォーマット

> 詳細ルール（Q1〜Q5 決定木・種別別注意点・JSON フォーマット例）は Phase 1 開始時に読み込む参照リファレンスに収録。

**ステップ記述の核心原則（3点）:**
1. **処理とエラー判定は必ず別ステップ**（1ステップにまとめない）
2. **外部呼び出し → `calls`、SOQL/DML → `object_ref`、条件分岐 → `decision` + `branch`**（Q1〜Q5 に従う）
3. **「判断できないから省略」は禁止**。必ずどれかの node_type を選択する

## Phase 1.5: 生成 JSON のセルフレビュー（スクリプト実行前に必ず実施）

全 JSON を生成し終えたら、**スクリプトを呼ぶ前に**以下を全件確認する。問題があれば修正してから Phase 2 へ進む。

### チェックリスト

- [ ] **決定木の適用漏れ**: 全ステップに対してステップ記述プロトコル（Q1〜Q5）を適用したか。`node_type: "process"` ばかりになっていないか（全部同じ図形 = 適用漏れのサイン）
- [ ] **object_ref / calls / branch の重複**: 同一ステップに複数が設定されていないか
- [ ] **node_type: "object" の使用禁止**: `"process"` + `object_ref` に統一
- [ ] **calls テキスト長**: 20文字以内か
- [ ] **抽象的タイトル禁止**: 「処理を実行」「データを取得」のような意味のないタイトルがないか
- [ ] **タイトルにクラス名・メソッド名を含めていないか**: クラス名・メソッド名は `method_name` フィールドに。`title` は日本語説明のみ
- [ ] **スコープ逸脱がないか**: 別Apexの内部実装を詳述していないか。外部呼び出しは `calls` + 高レベル説明にとどめているか
- [ ] **detail にコード混入禁止**: `detail` は日本語説明のみ。コードは sub_steps に
- [ ] **type フィールドの正確性**: このエージェントが扱うのは Apex/Batch/Flow/Integration のみ。LWC/画面フロー/Aura/Visualforce が混在していれば sf-screen-writer に委ねる
- [ ] **overview の品質**: 具体的なオブジェクト名・処理内容・連携先が含まれているか

チェックリストの確認後、必ずスクリプトで機械チェックを実行する:

```bash
python {project_dir}/scripts/python/sf-doc-mcp/check_design_json.py \
  --input "{tmp_dir}/{api_name}_design.json" \
  --type feature
```

- ERROR が出た場合: JSON を修正して再チェック。エラーが消えるまで Phase 2 へ進まない
- WARNING のみの場合: 内容を確認し、問題なければ続行してよい
- 「✅ 問題なし」が出た場合: Phase 2 へ進む

---

## Phase 2: 設計書 Excel の生成

全 JSON の生成完了後、`generate_feature_design.py` で Excel を生成する（このエージェントは常にこのスクリプトのみ使う）:

**Apex / Batch / Flow（非画面）/ Integration → generate_feature_design.py**:

> `--version-increment` の指定方法:
> - 既存の設計書がある場合（更新）→ `--version-increment minor`
> - 初回生成（既存ファイルなし）→ 省略可（スクリプトが自動判定して 1.0 から開始）
> - 大規模改修・破壊的変更がある場合 → `--version-increment major`

```bash
python {project_dir}/scripts/python/sf-doc-mcp/generate_feature_design.py \
  --input "{tmp_dir}/{api_name}_design.json" \
  --template "{project_dir}/scripts/python/sf-doc-mcp/プログラム設計書テンプレート.xlsx" \
  --output-dir "{output_dir}" \
  --version-increment {version_increment}
```

出力先フォルダとファイル名:
| 種別 | 出力先サブフォルダ | ファイル名 |
|---|---|---|
| Apex / Batch | `{output_dir}/apex/` | `【F-XXX】{name}.xlsx` |
| Flow（非画面）| `{output_dir}/flow/` | `【F-XXX】{name}.xlsx` |
| Integration | `{output_dir}/integration/` | `【F-XXX】{name}.xlsx` |

> 出力先とファイル名はスクリプトが自動決定する（type フィールドに基づく）。エージェントが手動で制御する必要はない。

---

## Phase 3: 機能一覧 Excel の生成

> **このエージェントが機能一覧を担当する**。sf-screen-writer が先に実行された場合は、その design JSON も `{tmp_dir}` に残っているので合わせて収集する。

まず `{tmp_dir}` 内の `*_design.json` 件数を確認する:

```bash
python -c "
import pathlib, sys
jsons = list(pathlib.Path(r'{tmp_dir}').glob('*_design.json'))
if not jsons:
    print('ERROR: *_design.json が 0 件です。Phase 1/2 でエラーが発生した可能性があります。')
    sys.exit(1)
print(f'{len(jsons)} 件の設計 JSON を検出。機能一覧を生成します。')
"
```

- 0 件の場合: 「設計 JSON が生成されていません。Phase 1/2 のエラーを確認してください。」と報告して終了する。Phase 4（クリーンアップ）は実行する。
- 1 件以上の場合: 以下の feature_list.json 組み立てへ進む。

`{tmp_dir}` 内の **全 `*_design.json`** から feature_list.json を組み立て、**必ず `{tmp_dir}/feature_list.json` に保存**してから実行する（sf-screen-writer 分の LWC/画面フロー JSON も含める）:

> **保存先は `{tmp_dir}/feature_list.json` のみ。output_dir やカレントディレクトリには絶対に保存しない。**

```json
[
  {
    "id": "F-001",
    "type": "Apex",
    "name": "機能名",
    "api_name": "ClassName",
    "overview": "設計JSONの overview フィールドをそのまま入れる（要約・省略しない）"
  }
]
```

> **重要**: `overview` は **Phase 1 で `{tmp_dir}/{api_name}_design.json` に保存した設計 JSON の `overview` フィールド**を使うこと。sf-doc から渡された `feature_list`（scan_features.py 出力）の `overview` は javadoc の1行抜粋であり品質が低いため、絶対に使わない。

既存の機能一覧.xlsx が `{output_dir}/機能一覧.xlsx` に存在する場合は `--source-file` で渡す（差分検出・バージョン管理に使用）:

```bash
# 既存ファイルあり（更新）
python {project_dir}/scripts/python/sf-doc-mcp/generate_feature_list.py \
  --input "{tmp_dir}/feature_list.json" \
  --output-dir "{output_dir}" \
  --author "{author}" \
  --project-name "{project_name}" \
  --version-increment {version_increment} \
  --source-file "{output_dir}/機能一覧.xlsx"

# 新規作成（初回）
python {project_dir}/scripts/python/sf-doc-mcp/generate_feature_list.py \
  --input "{tmp_dir}/feature_list.json" \
  --output-dir "{output_dir}" \
  --author "{author}" \
  --project-name "{project_name}" \
  --version-increment {version_increment}
```

---

## Phase 4: 後処理・完了報告

tmp_dir を削除し、output_dir およびプロジェクトルート（CWD）に残った一時ファイルも合わせてクリーンアップする:
```bash
python -c "
import shutil, pathlib
# tmp_dir を削除
shutil.rmtree(r'{tmp_dir}', ignore_errors=True)
# output_dir 直下に残ったゴミファイルを削除（.tmp* / *.json / *.py）
for p in pathlib.Path(r'{output_dir}').glob('*.json'):
    p.unlink(missing_ok=True)
for p in pathlib.Path(r'{output_dir}').glob('.tmp*'):
    if p.is_file():
        p.unlink(missing_ok=True)
    else:
        shutil.rmtree(p, ignore_errors=True)
for p in pathlib.Path(r'{output_dir}').glob('*.py'):
    p.unlink(missing_ok=True)
# プロジェクトルート（CWD）に残ったゴミファイルを削除（*_result.txt / *.py / 一時 .json）
cwd = pathlib.Path(r'{project_dir}')
for pat in ['*_result.txt', '*_tmp*.txt', '*_tmp*.json']:
    for p in cwd.glob(pat):
        p.unlink(missing_ok=True)
print('クリーンアップ完了')
"
```

> 削除完了後、`{tmp_dir}` / `{output_dir}` 直下 / `{project_dir}` 直下 に一時ファイルが残っていないことを確認する。

完了報告（sf-doc に返す）はクリーンアップ完了後に行う:

```
✅ 機能一覧.xlsx — 1ファイル（{機能数}件）
✅ 機能設計書.xlsx — {機能数}ファイル
出力先: {output_dir}
```

要確認事項があれば合わせて報告する（`docs/design/` 既存MDと内容が異なる場合・情報不足で TBD とした箇所など）。
