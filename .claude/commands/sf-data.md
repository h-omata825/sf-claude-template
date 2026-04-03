---
description: "組織のマスタデータ・メールテンプレート・レポート構成・データ統計を収集して記録する。実データは保存せず、構造・定義・集計値のみを記録する。"
---

salesforce-architectエージェントとして、組織のデータ関連情報を収集し、記録してください。

## セキュリティ原則

**このコマンドは「データの中身」ではなく「データの構造・定義・統計」を記録する。**

### 記録する
- マスタデータ（商品・価格表等、件数が少なく参照用のデータ）
- メールテンプレートの構成と本文
- レポート・ダッシュボード構成
- キュー・承認プロセスの構成
- データ統計（件数・分布・増加傾向 — 集計値のみ）
- データ品質指標（空欄率・重複率 — 数値のみ）

### 絶対に記録しない
- 取引先・取引先責任者・リードの実データ（社名・氏名・連絡先）
- 商談の具体的な金額・案件名
- メールアドレス・電話番号等の個人情報
- 添付ファイルの内容
- パスワード・トークン等の認証情報

---

## ユーザー入力

$ARGUMENTS

上記の入力がある場合、以下のように解釈する:
- **空（引数なし）** → **全カテゴリを一括収集（デフォルト）**
- **カテゴリ名**（「マスタ」「メール」「レポート」「統計」「品質」等）→ 指定カテゴリのみ収集
- **ファイルパス** → 既存のデータ関連資料を読み込んで統合
- **フォルダパス** → フォルダ内の資料を一括読み込み

### ファイル形式と読み込み方法
| 形式 | 方法 |
|---|---|
| .md, .txt, .csv, .json | Read ツールで直接読み込み |
| .pdf | Read ツールで読み込み（1回20ページまで） |
| .xlsx | Python (pandas) で自動変換して読み込み |
| .docx | Python (python-docx) で自動変換して読み込み |

### Excel / Word 変換手順
```bash
python -c "
import pandas as pd
import sys
xl = pd.ExcelFile(sys.argv[1])
for sheet_name in xl.sheet_names:
    df = pd.read_excel(xl, sheet_name=sheet_name)
    print(f'=== シート: {sheet_name} ===')
    print(df.to_markdown(index=False))
    print()
" "<ファイルパス>"
```

---

## 生成するファイル

```
docs/data/
├── _index.md               # データ情報のインデックス
├── master-data.md           # マスタデータ（商品・価格表・カスタム設定値等）
├── email-templates.md       # メールテンプレート一覧・本文
├── reports-dashboards.md    # レポート・ダッシュボード構成
├── automation-config.md     # キュー・承認プロセス・割り当てルール
├── data-statistics.md       # データ統計（件数・分布・傾向）
└── data-quality.md          # データ品質チェック結果
```

---

## Phase 0: コンテキスト読み込み

| ファイル | パス | 用途 |
|---|---|---|
| 組織プロフィール | `docs/overview/org-profile.md` | 用語集・オブジェクト構成 |
| オブジェクト定義書 | `docs/catalog/` | 項目構成・ピックリスト値 |

→ 存在しない場合は警告するが続行可能

---

## Phase 1: マスタデータの収集（master-data.md）

**「件数が少なく、全レコードを記録しても問題ないデータ」を対象とする。**

**重要: `sf` コマンドはGit Bashのパス問題を回避するため、失敗した場合は以下の形式で実行する:**
```bash
"C:/Program Files/sf/client/bin/node.exe" "C:/Program Files/sf/client/bin/run.js" <サブコマンド> <引数>
```

### 1-1. 商品マスタ（Product2）
```bash
sf data query -q "SELECT Name, ProductCode, Family, IsActive, Description FROM Product2 ORDER BY Family, Name" --json
```

### 1-2. 価格表（Pricebook2 + PricebookEntry）
```bash
sf data query -q "SELECT Name, IsActive, IsStandard FROM Pricebook2" --json
sf data query -q "SELECT Pricebook2.Name, Product2.Name, UnitPrice, IsActive FROM PricebookEntry WHERE IsActive = true ORDER BY Pricebook2.Name, Product2.Name" --json
```

### 1-3. カスタム設定の値
```bash
sf data query -q "SELECT DeveloperName, SetupOwnerId FROM <カスタム設定API名>__c" --json
```
→ org-profile.md にカスタム設定の一覧がある場合、それぞれの値を取得

### 1-4. カスタムメタデータの値
```bash
sf data query -q "SELECT DeveloperName, MasterLabel, <項目名> FROM <カスタムメタデータAPI名>__mdt" --json
```

### 1-5. その他マスタ系オブジェクト
以下の条件に合うカスタムオブジェクトもマスタとして収集する:
- レコード数が 500件以下
- オブジェクト名に「Master」「Setting」「Config」「Category」「Type」等が含まれる
- org-profile.md でマスタデータ系と分類されている

**件数チェック**を先に行い、500件超のものはスキップして統計情報のみ記録する。

### テンプレート（master-data.md）

```markdown
# マスタデータ

**最終更新日**: YYYY-MM-DD

---

## 商品マスタ（Product2）

レコード数: X件

| 商品名 | 商品コード | ファミリ | 有効 | 説明 |
|---|---|---|---|---|

---

## 価格表

### 価格表一覧
| 価格表名 | 標準 | 有効 |
|---|---|---|

### 価格表エントリ
| 価格表 | 商品 | 単価 |
|---|---|---|

---

## カスタム設定

### <カスタム設定名>
| DeveloperName | 値1 | 値2 | ... |
|---|---|---|---|

---

## カスタムメタデータ

### <メタデータ名>
| DeveloperName | MasterLabel | 値1 | 値2 | ... |
|---|---|---|---|---|
```

---

## Phase 2: メールテンプレートの収集（email-templates.md）

### 2-1. テンプレート一覧
```bash
sf data query -q "SELECT Name, DeveloperName, FolderId, Subject, TemplateType, IsActive, Description FROM EmailTemplate WHERE IsActive = true ORDER BY FolderId, Name" --json
```

### 2-2. テンプレート本文
```bash
sf data query -q "SELECT Name, Subject, Body, HtmlValue FROM EmailTemplate WHERE IsActive = true" --json
```
→ 差し込み項目（{!Contact.Name} 等）を抽出して一覧化する

### テンプレート（email-templates.md）

```markdown
# メールテンプレート

**最終更新日**: YYYY-MM-DD
**テンプレート数**: X件

---

## テンプレート一覧

| # | テンプレート名 | API名 | 種別 | 件名 | 用途（推定） |
|---|---|---|---|---|---|
| 1 | | | Text/HTML/Custom | | |

---

## テンプレート詳細

### [テンプレート名]
- **API名**: 
- **種別**: 
- **件名**: 
- **差し込み項目**: {!Contact.Name}, {!Opportunity.Amount}, ...

#### 本文
（テンプレートの本文をそのまま記録。差し込み項目はそのまま保持）

---
```

---

## Phase 3: レポート・ダッシュボードの収集（reports-dashboards.md）

### 3-1. レポート一覧
```bash
sf data query -q "SELECT Name, DeveloperName, FolderName, Format, Description FROM Report WHERE IsDeleted = false ORDER BY FolderName, Name" --json
```

### 3-2. ダッシュボード一覧
```bash
sf data query -q "SELECT Title, DeveloperName, FolderName, Description FROM Dashboard WHERE IsDeleted = false ORDER BY FolderName, Title" --json
```

### テンプレート（reports-dashboards.md）

```markdown
# レポート・ダッシュボード構成

**最終更新日**: YYYY-MM-DD

---

## レポート一覧

**レポート数**: X件

| # | フォルダ | レポート名 | 形式 | 説明 | 推定用途 |
|---|---|---|---|---|---|
| 1 | | | 表形式/サマリー/マトリクス/結合 | | |

### フォルダ別分類
（フォルダ名から推定される用途・対象部署を整理）

---

## ダッシュボード一覧

**ダッシュボード数**: X件

| # | フォルダ | ダッシュボード名 | 説明 | 推定用途 |
|---|---|---|---|---|

---

## 利用パターンの所見
- （どの業務指標を重視しているか）
- （レポートの傾向 — SFA系が多い / サービス系が多い等）
```

---

## Phase 4: 自動化・ワークフロー設定の収集（automation-config.md）

### 4-1. キュー
```bash
sf data query -q "SELECT Id, Name, DeveloperName FROM Group WHERE Type = 'Queue'" --json
```

### 4-2. キューのサポート対象オブジェクト
```bash
sf data query -q "SELECT Queue.Name, SobjectType FROM QueueSobject ORDER BY Queue.Name" --json
```

### 4-3. 承認プロセス（取得可能な範囲で）
```bash
sf data query -q "SELECT Id, EntityDefinitionId, DeveloperName, Description, IsActive FROM ProcessDefinition WHERE State = 'Active'" --json
```
→ エラーの場合は続行

### 4-4. 割り当てルール
```bash
sf data query -q "SELECT Name, SobjectType FROM AssignmentRule WHERE Active = true" --json
```
→ エラーの場合は続行

### テンプレート（automation-config.md）

```markdown
# 自動化・ワークフロー設定

**最終更新日**: YYYY-MM-DD

---

## キュー

| キュー名 | API名 | 対象オブジェクト | 推定用途 |
|---|---|---|---|

---

## 承認プロセス

| プロセス名 | 対象オブジェクト | 説明 | 推定用途 |
|---|---|---|---|

---

## 割り当てルール

| ルール名 | 対象オブジェクト | 推定用途 |
|---|---|---|

---

## 所見
- （業務フローの自動化パターン）
- （手動運用が残っている可能性がある箇所）
```

---

## Phase 5: データ統計の収集（data-statistics.md）

**実データではなく、集計値のみを記録する。**

### 5-1. 各オブジェクトのレコード件数
```bash
sf data query -q "SELECT COUNT() FROM <オブジェクト名>" --json
```

### 5-2. 主要項目の分布（ピックリスト系）
```bash
sf data query -q "SELECT <ピックリスト項目>, COUNT(Id) cnt FROM <オブジェクト名> GROUP BY <ピックリスト項目> ORDER BY COUNT(Id) DESC" --json
```
→ 主要オブジェクトの主要ピックリスト項目（StageName, Status 等）

### 5-3. 月次レコード作成数（増加傾向）
```bash
sf data query -q "SELECT CALENDAR_YEAR(CreatedDate) yr, CALENDAR_MONTH(CreatedDate) mo, COUNT(Id) cnt FROM <オブジェクト名> GROUP BY CALENDAR_YEAR(CreatedDate), CALENDAR_MONTH(CreatedDate) ORDER BY CALENDAR_YEAR(CreatedDate) DESC, CALENDAR_MONTH(CreatedDate) DESC LIMIT 12" --json
```
→ 主要オブジェクトの直近12ヶ月の作成件数

### テンプレート（data-statistics.md）

```markdown
# データ統計

**最終更新日**: YYYY-MM-DD

---

## レコード件数サマリ

| オブジェクト | 件数 | 前回比 | 傾向 |
|---|---|---|---|
| Account | X | +X | 増加/横ばい/減少 |

---

## 主要ピックリストの分布

### Opportunity — StageName（商談フェーズ）
| 値 | 件数 | 割合 |
|---|---|---|

### Case — Status
| 値 | 件数 | 割合 |
|---|---|---|

（他の主要ピックリストも同様）

---

## 月次レコード作成数

### Account
| 年月 | 作成件数 |
|---|---|

### Opportunity
| 年月 | 作成件数 |
|---|---|

---

## 所見
- （データ増加の傾向 — 急増/安定/停滞）
- （特定フェーズに偏りがないか）
- （直近で大きな変動があるか）
```

---

## Phase 6: データ品質チェック（data-quality.md）

### 6-1. 主要項目の空欄率
```bash
sf data query -q "SELECT COUNT(Id) FROM <オブジェクト名> WHERE <項目名> = null" --json
```
→ 主要なカスタム項目・必須でない重要項目について空欄率を計算

### 6-2. 重複の兆候
```bash
sf data query -q "SELECT Name, COUNT(Id) cnt FROM Account GROUP BY Name HAVING COUNT(Id) > 1 ORDER BY COUNT(Id) DESC LIMIT 10" --json
```
→ **件数のみ記録。具体的なレコード名は記録しない。**
→ 「Name が重複しているレコードが X件ある」という事実のみ

### テンプレート（data-quality.md）

```markdown
# データ品質チェック

**最終更新日**: YYYY-MM-DD

---

## 空欄率（主要項目）

| オブジェクト | 項目 | 空欄数 | 総数 | 空欄率 | 評価 |
|---|---|---|---|---|---|
| Account | Industry | X | X | X% | 良好/要改善/警告 |

### 評価基準
- 良好: 空欄率 20%未満
- 要改善: 空欄率 20-50%
- 警告: 空欄率 50%超

---

## 重複の兆候

| オブジェクト | 重複基準 | 重複グループ数 | 重複レコード数 | 評価 |
|---|---|---|---|---|
| Account | Name一致 | X | X | 良好/要改善/警告 |
| Contact | Email一致 | X | X | |

（具体的なレコード名・メールアドレスは記録しない。件数のみ。）

---

## 所見・推奨アクション
- （データ品質で特に気になる点）
- （重複マージの推奨）
- （必須項目の追加検討）
```

---

## Phase 7: インデックス生成

`docs/data/_index.md` を自動生成/更新する。

```markdown
# データ情報 インデックス

**最終更新日**: YYYY-MM-DD

---

| 資料 | パス | 内容 | 最終更新 |
|---|---|---|---|
| [マスタデータ](master-data.md) | 商品・価格表・カスタム設定値 | YYYY-MM-DD |
| [メールテンプレート](email-templates.md) | テンプレート一覧・本文 | YYYY-MM-DD |
| [レポート・ダッシュボード](reports-dashboards.md) | 構成・フォルダ分類 | YYYY-MM-DD |
| [自動化設定](automation-config.md) | キュー・承認・割り当て | YYYY-MM-DD |
| [データ統計](data-statistics.md) | 件数・分布・増加傾向 | YYYY-MM-DD |
| [データ品質](data-quality.md) | 空欄率・重複チェック | YYYY-MM-DD |
```

---

## Phase 8: 差分更新

既存ファイルがある場合:
1. 既存の全ファイルを読み込む
2. 組織データを再収集
3. 変更点を検出（マスタデータの追加/変更、統計値の変動等）
4. 手動で追記された情報（所見、推定用途等）は保持
5. `docs/changelog.md` に変更を記録

### changelog 記録フォーマット
```markdown
## YYYY-MM-DD /sf-data

**実行者**: （ユーザー名）
**更新ファイル**: docs/data/...

### 変更サマリ
- （マスタデータの変更）
- （統計値の大きな変動）
- （データ品質の変化）
```

---

## Phase 9: 報告

```
## 生成/更新ファイル
- docs/data/master-data.md — マスタデータ（商品X件、価格表X件、カスタム設定X件）
- docs/data/email-templates.md — メールテンプレート（X件）
- docs/data/reports-dashboards.md — レポートX件、ダッシュボードX件
- docs/data/automation-config.md — キューX件、承認プロセスX件
- docs/data/data-statistics.md — データ統計
- docs/data/data-quality.md — データ品質チェック

## 注目点
- （マスタデータで気になる点）
- （データ統計の傾向）
- （データ品質の問題）

## セキュリティ確認
- 実データ（社名・氏名・連絡先・金額等）は記録していません
- 記録しているのは集計値・定義・設定のみです
```

追加で収集したいデータカテゴリがあるか確認する。
