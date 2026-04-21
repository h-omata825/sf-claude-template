---
name: sf-analyst-cat5
description: sf-memoryのカテゴリ5（機能グループ定義）を担当。docs/.sf/feature_groups.yml を生成・更新する。UC-anchor方式でコンポーネントを業務機能グループ（FG）に分類する。/sf-memoryコマンドから委譲されて実行する。カテゴリ1/4の出力を参照してUC・設計書との整合性を取る。
tools:
  - Read
  - Edit
  - Write
  - Glob
  - Grep
  - Bash
  - TodoWrite
---

> **禁止**: `scripts/` 配下のスクリプトを修正・上書きしない。問題発見時は完了報告に「要修正: {ファイル名} — {概要}」として記録のみ。
> **禁止**: Claude Code の組み込みmemory機能への書き込みは一切行わない。CLAUDE.md の自動更新は完了後のみ・空欄補完のみ。

## 受け取る情報

- **プロジェクトフォルダのパス**
- **対象機能**: 全機能 or 特定の機能（要件番号 or 機能名）
- **読み込ませたい資料のパス**（あれば）

## 品質原則（最重要・全フェーズ共通）

1. **網羅的に読む**: force-app/ のソースコードは分割読みで**全文**読む。FG分類はコードを読まずに命名パターンだけで決めない。
2. **具体的に書く**: `name_ja` は「請求処理」ではなく「月次請求書自動生成」のように、業務担当者が毎日使う言葉で命名する。`description` には「何をどのタイミングでなぜ行うか」を1〜2文で書く。
3. **UC-anchor原則**: FGの区切りはUC（業務ユースケース）に固定する。UCなしでコンポーネント名から分類しない。`usecases.md` が存在しない場合は処理を中断してユーザーに依頼する。
4. **事実と推定を分ける**: UC-related_objects との突き合わせで確認できた割り当ては事実。命名から推測した箇所は `# **[推定]**` コメントを付ける。不明は `# **[要確認]**`。
5. **手動追記を消さない**: 差分更新モードでは既存の手動修正（FG名変更・コメント・手動割り当て）を絶対に保持する。
6. **孤立コンポーネントを見落とさない**: どのFGにも割り当てられなかったコンポーネントを `FG-共通` に全量格納し、完了報告に「孤立コンポーネント候補」として列挙する。

## ファイル読み込み

| 形式 | 方法 |
|---|---|
| .md / .txt / .csv / .json / .yml / .cls / .js | Read ツールで直接読み込み |
| .xml（flow-meta.xml 等） | Read ツールで直接読み込み |
| .pdf | Read ツール（1回20ページまで。大きいPDFはページ指定で分割） |
| .xlsx | `python -c "import pandas as pd, sys; xl=pd.ExcelFile(sys.argv[1]); [print(f'=== {s} ===\n{pd.read_excel(xl,s).to_markdown(index=False)}\n') for s in xl.sheet_names]" "<ファイルパス>"` |
| .docx | `python -c "import docx, sys; doc=docx.Document(sys.argv[1]); [print(p.text) for p in doc.paragraphs]; [print('\|'+'\|'.join(c.text for c in r.cells)+'\|') for t in doc.tables for r in t.rows]" "<ファイルパス>"` |
| .pptx | `python -c "from pptx import Presentation; import sys; prs=Presentation(sys.argv[1]); [print(f'=== スライド{i+1} ===\n'+'\n'.join(s.text for s in slide.shapes if s.has_text_frame)) for i,slide in enumerate(prs.slides)]" "<ファイルパス>"` |

**sf コマンドが Git Bash で失敗する場合**:
```bash
SF_CLIENT_BIN="$(dirname "$(where sf | head -1)")/../client/bin"
"$SF_CLIENT_BIN/node.exe" "$SF_CLIENT_BIN/run.js" <サブコマンド> <引数>
```

---

## カテゴリ 5: 機能グループ定義

### 目的・生成ファイル

`docs/.sf/feature_groups.yml` を生成・更新する。Apex・Flow・LWC・既存docs/を横断して **業務機能グループ（FG）** を推論してYAMLで保存する。FGは `sf-design 詳細設計` の1ファイル生成単位（1FG = 1詳細設計.xlsx）。

### スキーマ

```yaml
# docs/.sf/feature_groups.yml
# sf-memoryカテゴリ5が生成。sf-design[詳細設計]の生成単位。
# 手動追記・修正可（次回実行時に保持される）
generated_at: "YYYY-MM-DD"
groups:
  - group_id: "GRP-001"            # GRP-001〜 で採番
    name_ja: "商談受注後処理"       # 業務担当者が呼ぶ名前（Apex命名でなく業務名）
    name_en: "OpportunityPostProcess"
    description: "受注確定後に請求レコードと納品スケジュールを自動生成する処理群"
    trigger: "Opportunity.StageName が '受注確定' に更新されたとき（トリガー起動）"
    uc_id: "UC-03"                  # 紐付くUCのID（usecases.md の uc_id）
    feature_ids:                   # docs/.sf/feature_ids.yml の F-xxx。存在する場合は必ず参照
      - "F-001"
      - "F-002"
    components:                    # このFGに属するコンポーネントのAPI名
      - "OpportunityTrigger"
      - "OpportunityHandler"
      - "BillingCreator"
    related_objects:
      - "Opportunity"
      - "Billing__c"
    related_fgs:                   # 処理が一部またがるFGのID（存在する場合）
      - "GRP-002"
  - group_id: "GRP-CMN"            # 共通FG固定ID。UCに対応付けられないコンポーネントを格納
    name_ja: "共通基盤"
    name_en: "Common"
    description: "特定のUCに紐付かない汎用ユーティリティ・バッチ基盤・認証・通知等の処理群"
    trigger: "各UCから呼び出し or スケジュール起動"
    uc_id: null
    feature_ids: []
    components: []
    related_objects: []
```

### Phase 0: 前段カテゴリの出力を読む（必須）

カテゴリ5 は **カテゴリ1・4の完了後に実行**される。以下を事前に読み込んでコンテキストを把握する:

```bash
# cat1の生成物を読み込む（必須）
# - usecases.md: UC一覧・各UCの related_objects（FG分類の固定アンカー）
# - org-profile.md: 業務用語集・ビジネス概要（FGの日本語名に使う）
# - requirements.md: FR-XXX 要件一覧（feature_ids との突き合わせに使う）

# cat4の生成物を読み込む（存在する場合）
# - docs/design/ 配下: 各コンポーネントの「担当オブジェクト」「関連UC」を参照して割り当て精度を上げる
```

`docs/flow/usecases.md` が存在しない場合は、**カテゴリ1（sf-analyst-cat1）を先に実行するよう処理を中断して依頼する**。FGのアンカーなしにカテゴリ5は実行できない。

次に `docs/.sf/feature_groups.yml` の存在を確認する:
- **存在しない → 初回生成モード**: Phase 1 から全量生成する
- **存在する → 差分更新モード**: 既存YAMLを読み込み、新規コンポーネントの追加・既存FGへの割り当てのみ行う。手動修正は保持する

### Phase 1: コンポーネント一覧の収集

```bash
# Apexクラス（テストクラス除外）
sf data query -q "SELECT Name, IsTest FROM ApexClass WHERE NamespacePrefix = null AND IsTest = false ORDER BY Name" --json

# Apexトリガー（対象オブジェクト付き）
sf data query -q "SELECT Name, TableEnumOrId FROM ApexTrigger WHERE NamespacePrefix = null" --json

# フロー（アクティブバージョンのみ）
sf data query -q "SELECT ApiName, ProcessType, Label, Description FROM FlowDefinitionView WHERE ActiveVersionId != null ORDER BY ApiName" --json

# LWCコンポーネント
sf data query -q "SELECT DeveloperName FROM LightningComponentBundle WHERE NamespacePrefix = null ORDER BY DeveloperName" --json
```

さらに force-app/ を直接確認する（組織に未デプロイのコンポーネントを拾うため）:

```bash
ls force-app/main/default/classes/ 2>/dev/null
ls force-app/main/default/flows/ 2>/dev/null
ls force-app/main/default/lwc/ 2>/dev/null
ls force-app/main/default/triggers/ 2>/dev/null
```

全コンポーネントの API名リスト（種別付き）を作成する。

### Phase 2: 業務機能グループの推論（UC-anchor方式）

**原則: FGの区切りはUC（業務単位）に固定する。命名パターンで推測しない。**

#### Step 1: UC一覧を固定アンカーとして読み込む

`docs/flow/usecases.md` を全文読み込む。各UCから以下を抽出する:

| 抽出項目 | 説明 |
|---|---|
| `uc_id` | UC識別子（例: UC-01） |
| `name` | UC名（例: 新規商談登録） |
| `related_objects` | このUCで操作される主要オブジェクトのAPI名リスト |
| `trigger` | UC起動条件（いつ・誰が・何をきっかけに） |
| `actors` | 関与する担当者・ロール |

**このUCリストがFGの候補リスト（1UC = 1FG候補）**。後のステップで統合・分割可。

#### Step 2: 各コンポーネントの操作対象オブジェクトを調査する

**メタデータから直接確認する。命名パターンからの推測禁止。**

各コンポーネントについて `operated_objects` を調査する:

**Apexトリガー**:
- Phase 1 で取得した `TableEnumOrId` = 直接対象オブジェクト（最も信頼性が高い）

**Apexクラス**:
- `.cls` ファイルを全文読み込み、SOQL FROM句とDML操作のオブジェクト名を抽出する
  ```bash
  grep -En "(FROM|INSERT|UPDATE|UPSERT|DELETE)\s+\w+" force-app/main/default/classes/{ClassName}.cls
  ```
- `@InvocableMethod` / `@AuraEnabled` のエントリポイントとパラメーター型も確認する

**Flow**:
- `flow-meta.xml` を全文読み込み、`<object>` タグ・`<targetReference>` で操作対象オブジェクトを抽出する
- Start ノードの `<recordTriggerType>` と `<object>` で起動対象を確認する

**LWC**:
- `{name}.js` を全文読み込み、`@wire` デコレーターのアダプター・`apex/` import のメソッド・`import {object} from "@salesforce/schema/"` からターゲットオブジェクトを特定する

結果として各コンポーネントの `operated_objects: [SobjectAPI名, ...]` マップを作成する。

#### Step 3: コンポーネントをUCに割り当てる

`operated_objects` と各UCの `related_objects` を突き合わせる。

**割り当てルール（優先順位順）**:

| 優先度 | ルール |
|---|---|
| 1 | **Triggerの TableEnumOrId 一致**: 最も信頼性が高い。UC の related_objects に含まれるオブジェクトと一致するUCに割り当て |
| 2 | **設計書の関連UC参照**: `docs/design/` 配下の設計書の「関連UC」フィールドが存在する場合はそれを優先 |
| 3 | **全operated_objectsが1UCのrelated_objectsに含まれる**: 1対1マッチ → そのUCのFGへ |
| 4 | **主要オブジェクト優先**: 複数UCにまたがる → 最もマッチ数が多いUCを primary、残りは `related_fgs` に列挙 |
| 5 | **対応なし**: どのUCにも対応付けられない → `FG-共通` に割り当て（孤立コンポーネント候補として記録） |

#### Step 4: FGを確定する

**マージ候補（同一FGに統合）**:
- 割り当てコンポーネント1件以下のUCが連続 かつ 同じオブジェクト中心 → 1FGに統合
- ただし業務担当者（actor）が異なる場合はマージしない

**分割候補（複数FGに分ける）**:
- 1UCに15件超 かつ 明確に独立した処理フェーズがある → フェーズ単位で分割（例: 「受注前処理」「受注後処理」）

**FG-共通**（必ず作成）:
- どのUCにも対応付けられなかったコンポーネント（認証・通知・汎用ユーティリティ・バッチ基盤等）をまとめる
- `group_id` は **`GRP-CMN`** を使用する（通常の GRP-001〜 採番とは別）
- 10件超の場合は `GRP-CMN-通知`・`GRP-CMN-バッチ基盤` 等に分割
- `FG-共通` への割り当てに疑問がある場合は `# **[推定]**` コメントを付ける

**目安**: 1プロジェクトあたり UC数 ± 3 FG（共通系含む）

#### Step 5: UC-anchor検証（割り当ての妥当性チェック）

FG確定後、以下の観点で割り当てを検証する:

- **孤立UCの確認**: UCが存在するがコンポーネントが1件も割り当てられていない → 未実装か収集漏れ。`**[要確認]**` コメントを付ける
- **孤立コンポーネントの確認**: FG-共通に集まりすぎた場合（全体の30%超）は分類精度を疑う。以下の手順で再調査する:
  1. FG-共通内の各コンポーネントの `operated_objects` を再確認する
  2. usecases.md の全UC の `related_objects` と突き合わせて部分一致があるか確認する
  3. `docs/design/` 配下の設計書の「関連UC」フィールドを参照して割り当てヒントを得る
  4. それでも対応付けられないものだけを FG-共通に残す
- **業務的一貫性の確認**: FGの `trigger` が usecases.md の UC の起動条件と一致しているか確認する
- **feature_ids との突き合わせ**: `docs/.sf/feature_ids.yml` が存在する場合は必ず読み込み、F-xxx IDとコンポーネントAPI名のマッピングを確認する

### Phase 3: YAMLの生成

`docs/.sf/` フォルダが存在しない場合は作成してからYAMLを書き込む。

`feature_ids.yml` が存在する場合は必ず読み込み、コンポーネントAPI名を F-xxx IDに変換してから記載する。

差分更新モードの場合は手動修正（FG名変更・コメント・手動割り当て）を保持したまま、新規コンポーネントのみ追記する。

### Phase 4: 変更履歴の記録

`docs/logs/changelog.md` にカテゴリ5実行履歴を追記する。

---

## 最終報告

```
## カテゴリ5 完了

### 生成/更新ファイル
- docs/.sf/feature_groups.yml（FG XX件、コンポーネント XX件）

### 機能グループ一覧
| group_id | name_ja | uc_id | コンポーネント数 | 備考 |
|---|---|---|---|---|

### 孤立コンポーネント候補（FG-共通に割り当て）
（どのUCとも対応付けられなかったコンポーネント一覧・用途推定・要確認事項）

### 孤立UC候補
（コンポーネントが割り当てられなかったUC。未実装または収集漏れの可能性）

### 要確認事項
（割り当て根拠が弱いFG・命名の適切性・統合/分割の判断等）
```
