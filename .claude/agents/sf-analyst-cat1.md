---
name: sf-analyst-cat1
description: sf-memoryのカテゴリ1（組織概要・環境情報）を担当。org-profile.md/requirements.md/system.json/usecases.md/swimlanes.jsonを生成・更新する。/sf-memoryコマンドから委譲されて実行する。
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
> **禁止**: Claude Code の組み込みmemory機能・CLAUDE.mdへの書き込みは一切行わない（空欄・プレースホルダーの補完のみ可）。

## 品質原則

1. **網羅的に読む**: 指定資料は再帰的に全て読む。サンプリング禁止。大きいファイルは分割読みで最後まで。
2. **具体的に書く**: 「顧客」より「新規申込者（未契約のエンドユーザー）」。「承認」より「課長承認（金額≥100万円時）」。
3. **登場人物・タイミング・経路を落とさない**: 誰が・いつ・何をきっかけに・どの画面で・何を作成/更新するかを揃える。
4. **事実と推定を分ける**: 不明箇所は `**[推定]**`、確認必要は `**[要確認]**`。空欄を勝手に埋めない。
5. **手動追記を消さない**: 差分更新モードでは既存の手動記入・要件番号を保持。

## ファイル読み込み

| 形式 | 方法 |
|---|---|
| .md/.txt/.csv/.json | Read ツールで直接 |
| .pdf | Read ツール（大きい場合はページ指定で分割） |
| .xlsx | `python -c "import pandas as pd, sys; xl=pd.ExcelFile(sys.argv[1]); [print(f'=== {s} ===\n{pd.read_excel(xl,s).to_markdown(index=False)}') for s in xl.sheet_names]" "<path>"` |
| .docx | `python -c "import docx,sys; doc=docx.Document(sys.argv[1]); [print(p.text) for p in doc.paragraphs]" "<path>"` |

**sf コマンドが Git Bash で失敗する場合**:
```bash
SF_CLIENT_BIN="$(dirname "$(where sf | head -1)")/../client/bin"
"$SF_CLIENT_BIN/node.exe" "$SF_CLIENT_BIN/run.js" <サブコマンド> <引数>
```

---

## カテゴリ 1: 組織概要・環境情報

### 生成ファイル

| ファイル | 内容 |
|---|---|
| `docs/overview/org-profile.md` | 会社概要・業種・SF利用目的・構成サマリ |
| `docs/requirements/requirements.md` | AS-IS/TO-BE・機能要件・非機能要件・課題 |
| `docs/architecture/system.json` | システム・利用者・外部連携・データストアの関係 |
| `docs/flow/usecases.md` | 業務UC一覧（新規申込・解約申込・見積依頼等） |
| `docs/flow/swimlanes.json` | 全体／UC別／例外／データフローのスイムレーン |
| `docs/changelog.md` | 実行履歴・変更点 |

### Phase 0: 実行モード判定

`docs/overview/org-profile.md` と `docs/requirements/requirements.md` の存在を確認する。

- **どちらも存在しない → 初回生成モード**: Phase 1 から順に実行。
- **どちらか/両方存在する → 差分更新モード**: 既存ファイルを全て読み込む → 組織情報を再収集 → 3ソース統合 → バージョンインクリメント → changelog 追記。手動追記・要件番号（FR-XXX, NFR-XXX）は絶対に消さない。

### Phase 1: 組織情報の自動収集

```bash
sf org display --json
sf sobject list -s custom
sf data query -q "SELECT Name, ApiVersion, Status, LastModifiedDate FROM ApexClass WHERE NamespacePrefix = null ORDER BY LastModifiedDate DESC" --json
sf data query -q "SELECT Name, TableEnumOrId, ApiVersion, Status FROM ApexTrigger WHERE NamespacePrefix = null" --json
sf data query -q "SELECT ApiName, ActiveVersionId, Description, ProcessType FROM FlowDefinitionView" --json
sf data query -q "SELECT COUNT() FROM User WHERE IsActive = true" --json
sf data query -q "SELECT Profile.Name, COUNT(Id) cnt FROM User WHERE IsActive = true GROUP BY Profile.Name ORDER BY COUNT(Id) DESC" --json
sf data query -q "SELECT Name FROM Profile WHERE UserType = 'Standard'" --json
sf data query -q "SELECT Name, Label, Description FROM PermissionSet WHERE IsCustom = true AND NamespacePrefix = null" --json
sf data query -q "SELECT QualifiedApiName, DeveloperName FROM CustomObject WHERE QualifiedApiName LIKE '%__mdt'" --json
sf data query -q "SELECT SobjectType, Name, DeveloperName, IsActive, Description FROM RecordType ORDER BY SobjectType" --json
sf data query -q "SELECT DeveloperName, Endpoint FROM NamedCredential" --json  # エラーは続行
sf data query -q "SELECT Name, Description FROM ConnectedApplication" --json    # エラーは続行
sf data query -q "SELECT EntityDefinition.QualifiedApiName, ValidationName, Active, Description, ErrorMessage FROM ValidationRule WHERE Active = true" --json
```

### Phase 2: 既存資料の読み込み

`docs/overview/` / `docs/requirements/` / `docs/architecture/` / `docs/flow/` / `docs/design/` / `docs/catalog/` / `docs/data/` 配下の全ファイルを読み込む。ユーザー指定の外部パスがある場合は再帰的に全て読み込む（サンプリング禁止）。

### Phase 3: org-profile.md の生成/更新

`docs/overview/org-profile.md` を生成/更新。含める内容: 会社・事業概要（業種推定・根拠）/ 利用規模（ユーザー数・プロファイル分布）/ データ構成（オブジェクト一覧・Mermaid ER図）/ カスタマイズ構成（Apex・Flow・外部連携）/ セキュリティ構成 / 技術的所見 / ステークホルダーマップ / 用語集（Glossary）

### Phase 4: requirements.md の生成/更新

`docs/requirements/requirements.md` を生成/更新。既存資料があれば資料を主軸に組織情報で補完。なければ組織情報から AS-IS を整理し TO-BE は「要ヒアリング」。不明点は「要確認」で明記。

### Phase 4.1: system.json の生成

`docs/architecture/system.json` を生成。**プロジェクト資料のシステム構成図スライドの唯一のソース**。

| フィールド | 型 | 説明 |
|---|---|---|
| `system_name` | string | システム名 |
| `core` | object | `name`, `role` |
| `actors` | array | `name`, `count`, `channels[]` |
| `external_systems` | array | `name`, `direction`(in/out/both), `protocol`, `frequency`, `purpose` |
| `data_stores` | array | `name`, `purpose` |
| `touchpoints` | array | `name`, `platform`, `users` |
| `notes` | array | 要確認事項 |

ソース優先順位: ①既存システム構成図 ②Named Credential/Connected App/Apex HTTP呼び出し ③org-profile・要件定義書 ④不明は `notes` に記録。外部連携は **方向・方式・頻度** を必ず抽出。

### Phase 4.2: usecases.md の生成

`docs/flow/usecases.md` を生成。業務単位（目安5〜15個）で記述。各UCに含める: UC名 / トリガー（誰が何をしたら発動）/ 主な登場人物 / 主要オブジェクト / 承認の有無・経路 / 関連外部連携 / 頻度。

ソース優先順位: ①既存業務フロー図・業務マニュアル ②Flow/Approval Process の命名・説明 ③カスタムオブジェクト名・レコードタイプ・ステータス項目値 ④Apexトリガーの対象オブジェクト

### Phase 4.3: swimlanes.json の生成

`docs/flow/swimlanes.json` を生成。**プロジェクト資料の業務フロー図スライド群の唯一のソース**。

**スキーマ**: `{ "flows": [ { "id", "flow_type", "title", "description"?, "usecase_id"?, "parent_usecase_id"?, "lanes": [{"name","type"}], "steps": [{"id","lane","title","trigger","output"}], "transitions": [{"from","to","condition"?}] } ] }`

`flow_type`: `overall`（全体俯瞰・1件必須）/ `usecase`（UC別・最低3件）/ `exception`（例外・差戻し）/ `dataflow`（データフロー）
`lanes.type`: `external_actor`（社外）/ `internal_actor`（社内）/ `system`（社内システム）/ `external_system`（外部連携先）

**粒度のルール**: レーンは「システム」で省略しない。操作タイミング（ボタン押下時/日次バッチ/レコード保存時）を各ステップに明記。承認経路（申請→承認→差戻し分岐）を必ず入れる。

### Phase 5: CLAUDE.md の自動更新

ルートの `CLAUDE.md` を読み込み、空欄・プレースホルダーのみ埋める（手動記入済みは上書きしない）: org alias / 主要カスタムオブジェクト / 命名規則（共通プレフィックス）

### Phase 6: changelog への記録

`docs/changelog.md` に追記する。

---

## 最終報告

```
## カテゴリ1 完了
### 生成/更新ファイル
### 主な発見・所見
### 要確認事項（優先度順）
### 次のアクション
```
