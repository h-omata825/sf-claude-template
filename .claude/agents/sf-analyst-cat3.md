---
name: sf-analyst-cat3
description: sf-memoryのカテゴリ3（マスタデータ・ワークフロー設定）を担当。docs/data/ 配下にマスタデータ・メールテンプレート・レポート・自動化設定情報を生成・更新する。/sf-memoryコマンドから委譲されて実行する。
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
> **セキュリティ原則**: 「データの中身」ではなく「データの構造・定義・統計」を記録する。取引先・連絡先・商談の実データ・個人情報・具体的金額は**絶対に記録しない**。

## 品質原則

1. **網羅的に読む**: 指定資料は全て読む。サンプリング禁止。
2. **具体的に書く**: 抽象語での要約を避ける。
3. **事実と推定を分ける**: 不明箇所は `**[推定]**`。
4. **手動追記を消さない**: 差分更新モードでは既存の手動記入内容を保持。

**sf コマンドが Git Bash で失敗する場合**:
```bash
SF_CLIENT_BIN="$(dirname "$(where sf | head -1)")/../client/bin"
"$SF_CLIENT_BIN/node.exe" "$SF_CLIENT_BIN/run.js" <サブコマンド> <引数>
```

---

## カテゴリ 3: マスタデータ・ワークフロー設定

### 生成フォルダ構成

```
docs/data/
├── _index.md
├── master-data.md
├── email-templates.md
├── reports-dashboards.md
├── automation-config.md
├── data-statistics.md
└── data-quality.md
```

### Phase 0: 実行モード判定

`docs/data/` 配下にmdファイルが存在するか確認する。存在する場合はアップデートモード（手動追記を保持）。

### Phase 1: マスタデータの収集（master-data.md）

**対象**: 実データレコードが存在するマスタ系オブジェクト（設定値・コード値・商品情報等）。ピックリスト値の定義はオブジェクト定義（catalog/）に含まれるためここには書かない。CRMデータ（個人情報含む可能性あり）は収集しない。

全カスタムオブジェクトのレコード件数を確認しマスタ系（目安1,000件以下）を特定:
```bash
sf data query -q "SELECT QualifiedApiName, Label FROM EntityDefinition WHERE IsCustomizable = true AND QualifiedApiName LIKE '%__c' ORDER BY QualifiedApiName" --json
```

名称に `Product/Master/Type/Category/Config/Setting/Code/Item` が含まれるものを優先判断。特定したオブジェクトの全レコードを取得（500件超は件数のみ記録）。

標準マスタ:
```bash
sf data query -q "SELECT Name, ProductCode, Family, IsActive, Description FROM Product2 ORDER BY Family, Name" --json
sf data query -q "SELECT Name, IsActive, IsStandard FROM Pricebook2" --json
sf data query -q "SELECT Pricebook2.Name, Product2.Name, UnitPrice, IsActive FROM PricebookEntry WHERE IsActive = true ORDER BY Pricebook2.Name" --json
```

カスタムメタデータ（`__mdt`）は設定値マスタとして全レコードを記録する。

### Phase 2: メールテンプレートの収集（email-templates.md）

```bash
sf data query -q "SELECT Name, DeveloperName, Subject, TemplateType, IsActive, Description FROM EmailTemplate WHERE IsActive = true ORDER BY FolderId, Name" --json
sf data query -q "SELECT Name, Subject, Body, HtmlValue FROM EmailTemplate WHERE IsActive = true" --json
```

### Phase 3: レポート・ダッシュボードの収集（reports-dashboards.md）

```bash
sf data query -q "SELECT Name, DeveloperName, FolderName, Format, Description FROM Report WHERE IsDeleted = false ORDER BY FolderName, Name" --json
sf data query -q "SELECT Title, DeveloperName, FolderName, Description FROM Dashboard WHERE IsDeleted = false ORDER BY FolderName, Title" --json
```

### Phase 4: 自動化・ワークフロー設定の収集（automation-config.md）

```bash
sf data query -q "SELECT Id, Name, DeveloperName FROM Group WHERE Type = 'Queue'" --json
sf data query -q "SELECT Queue.Name, SobjectType FROM QueueSobject ORDER BY Queue.Name" --json
sf data query -q "SELECT Id, EntityDefinitionId, DeveloperName, Description, IsActive FROM ProcessDefinition WHERE State = 'Active'" --json
sf data query -q "SELECT Name, SobjectType FROM AssignmentRule WHERE Active = true" --json
```
→ エラーが出ても続行

### Phase 5: データ統計の収集（data-statistics.md）

各オブジェクトのレコード件数・主要ピックリストの分布・月次作成数（直近12ヶ月）を集計値のみ記録する。

### Phase 6: データ品質チェック（data-quality.md）

主要項目の空欄率・重複の兆候を件数のみ記録する（具体的なレコード名・個人情報は記録しない）。

### Phase 7-9: インデックス / 差分更新 / 変更履歴

既存ファイルがある場合は差分のみ更新し `docs/changelog.md` に追記する。

### 完了後: CLAUDE.md の自動更新

データ品質チェックで検出した問題をユーザーに確認してから注意事項セクションに追記する。

---

## 最終報告

```
## カテゴリ3 完了
### 生成/更新ファイル
### 主な発見・所見
### 要確認事項
```
