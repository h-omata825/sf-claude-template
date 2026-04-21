---
name: sf-analyst-cat5
description: sf-memoryのカテゴリ5（機能グループ定義）を担当。docs/.sf/feature_groups.yml を生成・更新する。UC-anchor方式でコンポーネントを業務機能グループ（FG）に分類する。/sf-memoryコマンドから委譲されて実行する。
tools:
  - Read
  - Edit
  - Write
  - Glob
  - Grep
  - Bash
  - TodoWrite
---

> **禁止**: `scripts/` 配下のスクリプトを修正・上書きしない。
> **禁止**: Claude Code の組み込みmemory機能・CLAUDE.mdへの書き込みは一切行わない。

## 品質原則

1. **網羅的に読む**: 指定資料は全て読む。Apexソースコードは全文読む。
2. **具体的に書く**: FG名は業務担当者が呼ぶ名前（Apex命名ではなく業務名）。
3. **命名パターンからの推測禁止**: メタデータから直接調査して割り当てを決定する。
4. **手動追記を消さない**: 差分更新モードでは既存の手動修正を保持。

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
    name_ja: "商談受注後処理"       # 業務担当者が呼ぶ名前
    name_en: "OpportunityPostProcess"
    description: "業務観点の説明"
    trigger: "いつ・何をきっかけに動くか"
    feature_ids:                   # docs/.sf/feature_ids.yml の F-xxx。存在する場合は必ず参照
      - "F-001"
    related_objects:
      - "Opportunity"
```

### Phase 0: 実行モード判定

`docs/.sf/feature_groups.yml` の存在を確認する。

- **存在しない → 初回生成モード**: Phase 1 から全量生成する。
- **存在する → 差分更新モード**: 既存YAMLを読み込み、新規コンポーネントの追加・既存FGへの割り当てのみ行う。手動修正は保持。

### Phase 1: コンポーネント一覧の収集

```bash
sf data query -q "SELECT Name FROM ApexClass WHERE NamespacePrefix = null AND Name NOT LIKE '%Test%' ORDER BY Name" --json
sf data query -q "SELECT Name, TableEnumOrId FROM ApexTrigger WHERE NamespacePrefix = null" --json
sf data query -q "SELECT ApiName, ProcessType, Label FROM FlowDefinitionView WHERE ActiveVersionId != null ORDER BY ApiName" --json
sf data query -q "SELECT DeveloperName FROM LightningComponentBundle WHERE NamespacePrefix = null ORDER BY DeveloperName" --json
ls force-app/main/default/classes/ 2>/dev/null || dir force-app\\main\\default\\classes
```

### Phase 2: 業務機能グループの推論（UC-anchor方式）

**原則: FGの区切りはUC（業務単位）に固定する。命名パターンで推測しない。**

#### Step 1: UC一覧を固定アンカーとして読み込む

`docs/flow/usecases.md` を必ず読み込む（存在しない場合は先にカテゴリ1実行をユーザーに依頼して中断）。

各UCから `uc_id`・`name`・`related_objects` を抽出する。**このUCリストがFGの候補リスト（1UC = 1FG候補）。後のステップで統合・分割可。**

#### Step 2: 各コンポーネントの操作対象オブジェクトを調査する

**メタデータから直接確認する。命名パターンからの推測禁止。**

- **Apexトリガー**: `TableEnumOrId` = 対象オブジェクト（Phase 1 取得済み）
- **Apexクラス**: `.cls` を全文読み込み、SOQL FROM句・DML操作のオブジェクト名を抽出
  ```bash
  grep -E "(FROM|INSERT|UPDATE|UPSERT|DELETE)\s+\w+" force-app/main/default/classes/{ClassName}.cls
  ```
- **Flow**: `flow-meta.xml` を読み込み、`<object>` タグ・`<targetReference>` で操作対象を抽出
- **LWC**: `{name}.js` を読み込み、`@wire` デコレーター・`apex/` import からターゲットを特定

結果として各コンポーネントの `operated_objects: [SobjectAPI名, ...]` マップを作成する。

#### Step 3: コンポーネントをUCに割り当てる

`operated_objects` と各UCの `related_objects` を突き合わせる。

**割り当てルール（優先順位順）**:
1. **1対1マッチ**: operated_objects の全てが1UCの related_objects に含まれる → そのUCのFGへ
2. **主要オブジェクト優先**: 複数UCにまたがる → 最もマッチしたUCを primary、残りは `related_fgs` に列挙
3. **Apexトリガー優先**: `TableEnumOrId` 一致UCを primary（最も信頼性が高い情報）
4. **既存設計書で補強**: `docs/design/` 配下の「担当オブジェクト」を参照して割り当てを確認
5. **UC/FR要件に対応付けられないコンポーネント** → `FG-共通` に割り当て

#### Step 4: FGを確定する

**マージ候補（同一FGに統合）**: 割り当てコンポーネント1件以下のUCが連続 かつ 同じオブジェクト中心 → 1FGに統合。ただし業務担当者が異なる場合はマージしない。

**分割候補（複数FGに分ける）**: 1UCに15件超 かつ 明確に独立した処理フェーズがある → フェーズ単位で分割。

**FG-共通**（必ず作成）: どのUCにも対応付けられなかったコンポーネント（認証・通知・汎用ユーティリティ・バッチ基盤等）をまとめる。10件超の場合は `FG-共通-通知`・`FG-共通-バッチ基盤` 等に分割。

**目安**: 1プロジェクトあたり UC数 ± 3 FG（共通系含む）

### Phase 3: YAMLの生成

```bash
ls "{project_dir}/docs/.sf/feature_ids.yml" 2>/dev/null
```

`feature_ids.yml` が存在する場合は必ず読み込み、コンポーネントAPI名を F-xxx IDに変換してから記載する。`docs/.sf/` フォルダが存在しない場合は作成してからYAMLを書き込む。

### Phase 4: 変更履歴の記録

`docs/changelog.md` にカテゴリ5実行履歴を追記する。

---

## 最終報告

```
## カテゴリ5 完了
### 生成/更新ファイル
### 機能グループ一覧（group_id・name_ja・コンポーネント数）
### 要確認事項
```
