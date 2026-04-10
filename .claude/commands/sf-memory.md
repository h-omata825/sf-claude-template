---
description: "Salesforce組織・プロジェクトの情報を収集し、docs/ 配下に情報ファイルを保存・更新するコマンド。組織概要・オブジェクト構成・マスタデータ・設計の4カテゴリを会話形式で選択して実行する。全て選択時はカテゴリごとにサブエージェントへ委譲してコンテキスト効率を最大化する。"
---

> **注意**: このコマンドはClaude Codeの組み込みmemory機能・CLAUDE.mdへの書き込みは一切行わない。
> 全ての出力は `docs/` 配下のMarkdownファイルへの保存のみで行う。

salesforce-architectエージェントとして、Salesforce組織・プロジェクトの情報を収集し、`docs/` 配下に情報ファイルを保存・更新してください。

---

## Step 0: 対象の選択（会話形式）

最初に以下を確認する。

```
どの範囲の記憶形成を行いますか？

  1. 全て（初回セットアップ推奨）
  2. 組織概要・環境情報
  3. オブジェクト・項目構成
  4. マスタデータ・自動化
  5. 設計・機能仕様

番号または名前で選択してください（複数可 例: 2 3）
```

### 2〜5 が選択された場合（カテゴリ指定）

**カテゴリ3「オブジェクト・項目構成」の場合:**
```
対象を指定しますか？
  a. 全オブジェクト（デフォルト）
  b. 特定のオブジェクト（API名を入力 例: Quote__c, Account）
```

**カテゴリ5「設計・機能仕様」の場合:**
```
対象を指定しますか？
  a. 全機能（要件定義書の全FR）
  b. 特定の機能（要件番号 or 機能名を入力 例: FR-007, 見積管理）
  c. 逆引き（force-app/ のコードから設計書を生成）
  d. 既存資料の取り込み（ファイルパスを入力）
```

### 読み込ませたい資料がある場合

全カテゴリ共通で、以下を確認する:
```
読み込ませたい資料（企画書・要件書・設計書・既存定義書等）はありますか？
  - ファイルパスを指定してください（複数可。.xlsx/.docx/.pdf/.md 対応）
  - なければそのままEnterで進んでください
```

---

## 実行フロー

### 「全て」選択時 — サブエージェント委譲（初回推奨）

コンテキスト効率を最大化するため、カテゴリごとにサブエージェントへ委譲する。
各サブエージェントはクリーンなコンテキストで起動し、自分のカテゴリだけに集中して docs/ へ保存し、サマリだけを返す。

```
Step 1: カテゴリ1 をサブエージェントへ委譲
  Agent（カテゴリ1: 組織概要・環境情報）
    → docs/overview/org-profile.md, docs/requirements/requirements.md を生成
    → 完了サマリを返す

Step 2: カテゴリ2・3・4 を並列でサブエージェントへ委譲
  ※ カテゴリ1完了後に実行（org-profile.md を参照するため）
  Agent（カテゴリ2: オブジェクト・項目構成）  ┐
  Agent（カテゴリ3: マスタデータ・自動化）    ├ 並列実行
  Agent（カテゴリ4: 設計・機能仕様）          ┘
    → 各カテゴリの docs/ を生成
    → 完了サマリを返す

Step 3: 2周目（横断補完）
  全 docs/ を読み込んで以下を実行:
  - 用語の統一（カテゴリ間の表記ゆれ修正）
  - カテゴリ間の矛盾・不整合の解消
  - 「要確認」事項を他カテゴリの情報で補完
  - org-profile.md の用語集を各定義書・設計書に反映
```

#### サブエージェントへの委譲方法

Agent ツールを使用し、各カテゴリの指示を self-contained なプロンプトで渡す。
プロンプトには以下を含める:
- 実行するカテゴリ名と対象範囲
- 読み込む既存 docs/ のパス
- 読み込ませたい資料のパス（Step 0 で指定があった場合）
- このコマンドファイルの該当カテゴリセクション全文

#### ユーザーへの報告（各ステップ完了時）

```
✅ カテゴリ1 完了 — org-profile.md, requirements.md を生成しました
✅ カテゴリ2 完了 — オブジェクト定義書 X件 を生成しました
✅ カテゴリ3 完了 — マスタデータ・自動化情報を記録しました
✅ カテゴリ4 完了 — 設計書 X件 を生成しました
🔄 2周目（横断補完）を実行中...
```

### カテゴリ指定時 — サブエージェント委譲

カテゴリ指定時も同様にサブエージェントへ委譲する。

理由: このコマンドファイル全文（800行超）がコンテキストに乗った状態で実行するより、
カテゴリの指示だけをクリーンなコンテキストで受け取るサブエージェントの方が
元の4コマンドを直接実行していた時と同等の集中度で動作できるため。

```
Agent（指定カテゴリ）
  → 指示: 対象カテゴリの全 Phase + 既存 docs/ のパス + 資料パス（あれば）
  → 完了サマリを返す
```

---

## 共通: ファイル読み込み方法

| 形式 | 方法 |
|---|---|
| .md, .txt, .csv, .json | Read ツールで直接読み込み |
| .pdf | Read ツールで読み込み（1回20ページまで。大きいPDFはページ指定で分割） |
| .xlsx | Python で自動変換して読み込み（下記参照） |
| .docx | Python で自動変換して読み込み（下記参照） |

### .xlsx の変換
```bash
python -c "
import pandas as pd
import sys
file_path = sys.argv[1]
xl = pd.ExcelFile(file_path)
for sheet_name in xl.sheet_names:
    df = pd.read_excel(xl, sheet_name=sheet_name)
    print(f'=== シート: {sheet_name} ===')
    print(df.to_markdown(index=False))
    print()
" "<ファイルパス>"
```

### .docx の変換
```bash
python -c "import docx; print('OK')" 2>/dev/null || pip install python-docx
python -c "
import docx, sys
doc = docx.Document(sys.argv[1])
for para in doc.paragraphs:
    print(para.text)
for table in doc.tables:
    for row in table.rows:
        print('| ' + ' | '.join(cell.text for cell in row.cells) + ' |')
" "<ファイルパス>"
```

**重要: `sf` コマンドがGit Bashで失敗した場合は以下で実行する:**
```bash
"C:/Program Files/sf/client/bin/node.exe" "C:/Program Files/sf/client/bin/run.js" <サブコマンド> <引数>
```

---

## カテゴリ 1: 組織概要・環境情報

### 生成ファイル

| ファイル | パス | 内容 |
|---|---|---|
| 組織プロフィール | `docs/overview/org-profile.md` | 会社概要・業種・SF利用目的・構成サマリ |
| 要件定義書 | `docs/requirements/requirements.md` | AS-IS/TO-BE・機能要件・非機能要件・課題 |
| 変更履歴 | `docs/changelog.md` | 実行履歴・変更点の記録 |

### Phase 0: 実行モード判定

`docs/overview/org-profile.md` と `docs/requirements/requirements.md` の存在を確認する。

**どちらも存在しない → 初回生成モード**: Phase 1 から順に実行し新規ファイルを生成する。

**どちらか/両方存在する → 差分更新モード**:

| ソース | 何を使うか |
|---|---|
| 組織メタデータ（再収集） | 新規追加・変更・削除の検出 |
| 既存ドキュメント | 前回の内容・手動追記を保持 |
| 現在のセッション情報 | 会話の中で確認・判明した事実・決定事項 |

手順: 既存ファイルを全て読み込む → 組織情報を再収集 → 3つのソースを統合 → バージョンをインクリメント → changelog に追記

差分更新ルール:
- **手動追記は絶対に消さない**
- **要件番号（FR-XXX, NFR-XXX）は維持**（新規は続番で採番）
- **「推定」→「確定」への昇格**: セッション・手動修正で確定した情報はラベルを更新
- **バージョン番号は必ずインクリメント**

### Phase 1: 組織情報の自動収集

#### 1-1. 組織基本情報
```bash
sf org display --json
```
→ 組織ID、インスタンスURL、APIバージョン、ユーザー名、組織タイプを取得

#### 1-2. カスタムオブジェクト一覧
```bash
sf sobject list -s custom
```

#### 1-3. 主要オブジェクトの項目構成
カスタムオブジェクトと主要標準オブジェクト（Account, Contact, Opportunity, Case, Lead）:
```bash
sf sobject describe -s <オブジェクト名> --json
```

#### 1-4. Apexクラス一覧
```bash
sf data query -q "SELECT Name, ApiVersion, Status, CreatedDate, LastModifiedDate FROM ApexClass WHERE NamespacePrefix = null ORDER BY LastModifiedDate DESC" --json
```

#### 1-5. Apexトリガー一覧
```bash
sf data query -q "SELECT Name, TableEnumOrId, ApiVersion, Status FROM ApexTrigger WHERE NamespacePrefix = null" --json
```

#### 1-6. Flow一覧
```bash
sf data query -q "SELECT ApiName, ActiveVersionId, Description, ProcessType FROM FlowDefinitionView" --json
```

#### 1-7. レコード件数（主要オブジェクト）
```bash
sf data query -q "SELECT COUNT() FROM <オブジェクト名>" --json
```

#### 1-8. 有効ユーザー数・ライセンス情報
```bash
sf data query -q "SELECT COUNT() FROM User WHERE IsActive = true" --json
sf data query -q "SELECT Profile.Name, COUNT(Id) cnt FROM User WHERE IsActive = true GROUP BY Profile.Name ORDER BY COUNT(Id) DESC" --json
```

#### 1-9. プロファイル・権限セット
```bash
sf data query -q "SELECT Name FROM Profile WHERE UserType = 'Standard'" --json
sf data query -q "SELECT Name, Label, Description FROM PermissionSet WHERE IsCustom = true AND NamespacePrefix = null" --json
```

#### 1-10. カスタム設定・カスタムメタデータ
```bash
sf data query -q "SELECT QualifiedApiName, DeveloperName FROM CustomObject WHERE QualifiedApiName LIKE '%__mdt'" --json
```

#### 1-11. レコードタイプ一覧
```bash
sf data query -q "SELECT SobjectType, Name, DeveloperName, IsActive, Description FROM RecordType ORDER BY SobjectType" --json
```

#### 1-12. Named Credential（外部連携）
```bash
sf data query -q "SELECT DeveloperName, Endpoint FROM NamedCredential" --json
```
→ エラーが出ても続行

#### 1-13. 接続アプリケーション
```bash
sf data query -q "SELECT Name, Description FROM ConnectedApplication" --json
```
→ エラーが出ても続行

#### 1-14. 入力規則の一覧
```bash
sf data query -q "SELECT EntityDefinition.QualifiedApiName, ValidationName, Active, Description, ErrorMessage FROM ValidationRule WHERE Active = true" --json
```
→ エラーが出ても続行

### Phase 2: 既存資料の読み込み

以下のフォルダに既存資料があれば全て読み込む:
- `docs/overview/` — 組織概要・会社情報
- `docs/requirements/` — 要件定義書・企画書・ヒアリングメモ
- `docs/design/` — 設計書
- `docs/catalog/` — オブジェクト・項目定義書
- `docs/data/` — データ統計・マスタデータ

初回生成モードでファイルがない場合はユーザーに確認（Step 0 で資料指定がなかった場合）:
```
プロジェクトの企画書・要件書・ヒアリングメモなどはありますか？
  - ファイルパスを指定してください（複数可）
  - なければ「なし」と入力してください（組織情報のみで解析します）
```

### Phase 3: 組織プロフィールの生成/更新

`docs/overview/org-profile.md` を生成（または更新）する。

```markdown
# 組織プロフィール

**生成日**: YYYY-MM-DD
**最終更新日**: YYYY-MM-DD
**組織ID**: <組織ID>
**インスタンスURL**: <URL>
**APIバージョン**: <バージョン>

---

## 会社・事業概要

| 項目 | 内容 |
|---|---|
| 推定業種 | （根拠も記載） |
| 推定事業内容 | |
| Salesforce利用目的 | （SFA / サービス / マーケティング / カスタムアプリ / 複合型） |
| 利用開始時期（推定） | |

### 推定の根拠
（なぜその業種・事業内容と判断したかを箇条書きで説明）

---

## 利用規模

| 項目 | 数値 |
|---|---|
| 有効ユーザー数 | X名 |
| プロファイル数 | X種 |
| カスタム権限セット数 | X個 |

### ユーザー分布
| プロファイル | ユーザー数 | 推定ロール |
|---|---|---|

---

## データ構成

### オブジェクト概要
| オブジェクト | 種別 | レコード数 | カスタム項目数 | レコードタイプ数 | 業務上の役割（推定） |
|---|---|---|---|---|---|

### データモデル（ER図）
```mermaid
erDiagram
    （主要オブジェクトのリレーションを図示）
```

### データ規模の所見

---

## カスタマイズ構成

### カスタマイズ度
| カテゴリ | 数量 | 評価 |
|---|---|---|
| カスタムオブジェクト | X個 | |
| Apexクラス | X個 | |
| Apexトリガー | X個 | |
| フロー | X個 | |
| カスタムメタデータ | X個 | |
| **総合カスタマイズ度** | | **低 / 中 / 高** |

### Apex クラス（主要なもの）
| クラス名 | APIバージョン | 最終更新日 | 推定用途 |
|---|---|---|---|

### フロー
| フロー名 | 種別 | 状態 | 説明 |
|---|---|---|---|

### 外部連携の兆候

---

## セキュリティ構成

### プロファイル一覧
| プロファイル名 | 推定用途 |
|---|---|

### カスタム権限セット
| 権限セット名 | 説明 | 推定用途 |
|---|---|---|

---

## 技術的所見

### 健全性チェック
| チェック項目 | 状態 | 詳細 |
|---|---|---|
| APIバージョンの統一性 | OK/注意/警告 | |
| 未使用コードの兆候 | OK/注意/警告 | |
| フローの整理状態 | OK/注意/警告 | |
| 自動化の複雑度 | OK/注意/警告 | |

### 改善提案

---

## ステークホルダーマップ

| ユーザー区分 | 推定人数 | 主な利用機能 | 利用シナリオ（推定） |
|---|---|---|---|

---

## 用語集（Glossary）

（**Claude Code が出力の文脈を合わせるために最も重要なセクション。差分更新時も積極的に拡充する**）

| 業務用語（推定） | Salesforce上の表現 | API名 | 備考 |
|---|---|---|---|

### レコードタイプ別の業務区分
| オブジェクト | レコードタイプ | 業務上の意味（推定） |
|---|---|---|
```

### Phase 4: 要件定義書の生成/更新

`docs/requirements/requirements.md` を生成（または更新）する。

生成ルール:
- 既存資料がある場合: 資料の内容を主軸に、組織情報で補完・裏付け
- 既存資料がない場合: 組織情報から逆引きで現状（AS-IS）を整理し、TO-BEは「要ヒアリング」
- 推測で埋めない: 不明な点は「要確認」として明記
- 差分更新時: 既存の要件番号・手動修正を保持し、新規分のみ追加

（テンプレートは通常の要件定義書フォーマット: 背景・目的・AS-IS・TO-BE・機能要件・非機能要件・ビジネスルール・未解決事項）

### Phase 5: CLAUDE.md の自動更新

ルートの `CLAUDE.md` を読み込み、以下を更新する。**手動記入済みの内容は上書きしない。空欄・プレースホルダーのみ埋める。**

- Salesforce組織情報（org alias）: 実際のエイリアスと接続先URLを反映
- 主要カスタムオブジェクト: 検出されたカスタムオブジェクトを列挙
- 命名規則: Apexクラス名・カスタムオブジェクト名から共通プレフィックスを検出した場合に反映

### Phase 6: 変更履歴の記録

`docs/changelog.md` に追記する。

---

## カテゴリ 2: オブジェクト・項目構成

### 生成ファイル

```
docs/catalog/
├── _index.md           # 全オブジェクトのインデックス
├── _data-model.md      # 全体ER図・リレーション一覧
├── standard/           # 標準オブジェクト
└── custom/             # カスタムオブジェクト
```

### Phase 0: 実行モード判定

`docs/catalog/` 配下にmdファイルが存在するか確認する。

**存在しない → 初回生成モード**: Phase 1 へ進む。参照コンテキスト（あれば）: `docs/overview/org-profile.md`, `docs/requirements/requirements.md`

**存在する → アップデートモード**:

| ソース | 使い方 |
|---|---|
| 組織メタデータ（再収集） | 項目の追加・変更・削除を検出 |
| 既存の定義書 | 手動追記・確定済み情報を保持 |
| 現在のセッション情報 | 会話で判明した業務ルール・用語・確定事項 |

重要ルール:
- 手動追記・業務上のメモは絶対に消さない
- 「推定」→「確定」への昇格はセッション情報を根拠に行う

### Phase 1: 処理対象の決定

#### 全オブジェクト対象の場合

カスタムオブジェクト一覧を取得:
```bash
sf sobject list -s custom
```

標準オブジェクトの使用状況確認（レコード件数で判定）:
```bash
sf data query -q "SELECT COUNT() FROM Account" --json
sf data query -q "SELECT COUNT() FROM Contact" --json
sf data query -q "SELECT COUNT() FROM Lead" --json
sf data query -q "SELECT COUNT() FROM Opportunity" --json
sf data query -q "SELECT COUNT() FROM Case" --json
sf data query -q "SELECT COUNT() FROM Campaign" --json
sf data query -q "SELECT COUNT() FROM Product2" --json
sf data query -q "SELECT COUNT() FROM Task" --json
sf data query -q "SELECT COUNT() FROM Event" --json
```
→ 件数 > 0、またはカスタム項目が存在するものを対象に含める

処理開始前に対象一覧を表示する（確認不要、そのまま実行）:
```
## 処理対象
- 標準オブジェクト（使用中）: Account（X件）, ...（計X件）
- カスタムオブジェクト: XXX__c, YYY__c（X件）
- 合計: X件

処理を開始します...
```

#### 特定オブジェクト指定の場合

指定されたオブジェクトのみ処理する。

### Phase 2: 組織メタデータの収集

対象オブジェクトごとに実行:

```bash
sf sobject describe -s <オブジェクト名> --json
```

抽出する情報:
- 基本情報: API名、表示名、キープレフィックス
- 全項目: 項目名、API名、データ型、長さ、必須、一意、デフォルト値
- リレーション: lookupRelationship, masterDetail の関連先
- レコードタイプ: 名前、DeveloperName、アクティブ/非アクティブ
- 入力規則: 入力規則名、数式、エラーメッセージ
- ピックリスト値: 各項目の選択肢一覧

```bash
sf data query -q "SELECT COUNT() FROM <オブジェクト名>" --json
```

### Phase 3: オブジェクト定義書の生成

各オブジェクトに対して `docs/catalog/{standard|custom}/<オブジェクト名>.md` を生成する。

（テンプレート: 基本情報・リレーション・ER図・レコードタイプ・標準項目・カスタム項目・ピックリスト値・数式項目・入力規則・自動化・権限マトリクス・所見）

### Phase 4: 全体データモデル図の生成

全オブジェクト処理後、`docs/catalog/_data-model.md` を生成する（全体ER図・リレーション一覧・オブジェクト分類）。

### Phase 5: インデックス生成

`docs/catalog/_index.md` を生成/更新する（標準・カスタムオブジェクトの一覧・件数・バージョン）。

### Phase 6: 差分更新

既存定義書がある場合: 新規追加・削除・変更された項目を検出し、手動追記を保持した上で更新。バージョンをインクリメントし changelog に追記。

### Phase 7: 変更履歴の記録

`docs/changelog.md` に追記する。

### 完了後: CLAUDE.md の自動更新

主要カスタムオブジェクトと命名規則（項目のプレフィックス等）を更新する。

---

## カテゴリ 3: マスタデータ・自動化

**セキュリティ原則: 「データの中身」ではなく「データの構造・定義・統計」を記録する。**

記録する: マスタデータ・メールテンプレート・レポート/ダッシュボード構成・キュー/承認プロセス・データ統計（集計値のみ）・データ品質指標（数値のみ）

絶対に記録しない: 取引先・連絡先・リードの実データ・商談の具体的金額・個人情報・パスワード等

### 生成ファイル

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

`docs/data/` 配下にmdファイルが存在するか確認する。

**存在しない → 初回生成モード**: 参照コンテキスト: `docs/overview/org-profile.md`, `docs/catalog/`（存在しない場合は警告して続行）

**存在する → アップデートモード**:

| ソース | 使い方 |
|---|---|
| 組織データ（再収集） | データの変化を検出 |
| 既存の資料 | 手動追記・補足メモを保持 |
| 現在のセッション情報 | データの意味・業務上の使われ方を反映 |

### Phase 1: マスタデータの収集（master-data.md）

「件数が少なく全レコードを記録しても問題ないデータ」を対象とする（目安: 500件以下）。

```bash
sf data query -q "SELECT Name, ProductCode, Family, IsActive, Description FROM Product2 ORDER BY Family, Name" --json
sf data query -q "SELECT Name, IsActive, IsStandard FROM Pricebook2" --json
sf data query -q "SELECT Pricebook2.Name, Product2.Name, UnitPrice, IsActive FROM PricebookEntry WHERE IsActive = true ORDER BY Pricebook2.Name, Product2.Name" --json
```

カスタム設定・カスタムメタデータの値も収集する。

### Phase 2: メールテンプレートの収集（email-templates.md）

```bash
sf data query -q "SELECT Name, DeveloperName, FolderId, Subject, TemplateType, IsActive, Description FROM EmailTemplate WHERE IsActive = true ORDER BY FolderId, Name" --json
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

### Phase 7: インデックス生成

`docs/data/_index.md` を生成/更新する。

### Phase 8: 差分更新 / Phase 9: 変更履歴の記録

既存ファイルがある場合は差分のみ更新し changelog に追記する。

### 完了後: CLAUDE.md の自動更新

データ品質チェックで検出した問題をユーザーに確認してから注意事項セクションに追記する。

---

## カテゴリ 4: 設計・機能仕様

### 設計書のフォルダ構成

```
docs/design/
├── apex/           # Apexクラス・トリガーの設計書
├── flow/           # フロー
├── batch/          # バッチ Apex・スケジュールジョブ
├── lwc/            # Lightning Web Components
├── integration/    # 外部連携
├── config/         # 宣言的設定（入力規則・数式・ページレイアウト等）
└── _index.md       # 全設計書のインデックス
```

### Phase 0: 実行モード判定

`docs/design/` 配下にmdファイルが存在するか確認する。

**存在しない → 初回生成モード**: 以下を読み込む（存在しない場合は警告して続行）:
- `docs/overview/org-profile.md`
- `docs/requirements/requirements.md`

**存在する → アップデートモード**:

| ソース | 使い方 |
|---|---|
| 既存の設計書 | 設計内容・手動追記・確定済み判断を保持 |
| 上流資料（要件定義・org-profile） | 要件との整合性確認・変更点の反映 |
| 現在のセッション情報 | 確認した仕様・設計判断の根拠・修正内容を反映 |

重要ルール:
- 手動追記・設計判断の根拠は絶対に消さない
- セッションで確定した仕様は「要確認」→「確定」に昇格
- 既存設計との矛盾が生じた場合は変更点を明記してユーザーに確認する

### Phase 1: 処理モードの実行

#### 全機能対象の場合（モード A）

要件定義書の機能要件一覧を読み、設計書の作成計画を提示する:
```
## 設計書 作成計画

| # | 要件 | フォルダ | 設計書 | 状態 |
|---|---|---|---|---|
| FR-001 | 商談管理機能 | apex/ | FR-001_opportunity-management.md | 未作成 |
| FR-002 | ケース自動振り分け | flow/ | FR-002_case-routing.md | 作成済み（v1.0） |

全て作成します...
```

#### 特定機能指定の場合（モード B）

指定された機能の設計書のみ生成する。

#### 逆引き生成（モード C）

`force-app/` 内の既存Apex・フロー・トリガーを読んで設計書を逆引き生成する。

1. 対象一覧の取得:
```bash
sf data query -q "SELECT Name FROM ApexClass WHERE NamespacePrefix = null ORDER BY Name" --json
sf data query -q "SELECT Name, TableEnumOrId FROM ApexTrigger WHERE NamespacePrefix = null" --json
sf data query -q "SELECT ApiName, ProcessType FROM FlowDefinitionView WHERE ActiveVersionId != null" --json
```
2. 対象をユーザーに提示し確認する
3. 各コンポーネントのコードを読む（`force-app/main/default/classes/`, `triggers/`, `flows/`）
4. 設計書を逆引き生成する（推定部分は「逆引き（推定）」と明記）

#### 既存資料の取り込み（モード D）

指定されたファイル/フォルダを読み込み、標準フォーマットに変換・統合する。
大量ファイルの場合は分割して処理し、インポート計画をユーザーに提示してから実行する。

### Phase 2: 設計書の生成

#### ファイル命名規則
```
docs/design/{種別フォルダ}/{要件番号}_{機能名-kebab-case}.md
```
要件番号がない場合: `MISC-XXX_{機能名}.md`

（テンプレート: 概要・スコープ・ユーザーストーリー・関連要件・実現方式・データ設計・業務フロー・画面設計・ロジック設計・バリデーション・権限設計・外部連携・テスト観点・ガバナ制限・影響範囲・未解決事項・受入基準）

### Phase 3: インデックス生成

`docs/design/_index.md` を生成/更新する。

### Phase 4: 差分更新 / Phase 5: 変更履歴の記録

既存設計書がある場合は差分のみ更新し changelog に追記する。

### 完了後: CLAUDE.md の自動更新

設計で確定した命名規則・制約・新規オブジェクトをユーザーに確認してから更新する。

---

## 全て選択時: 2周目（横断的補完）

全4カテゴリの1周目完了後に実行する。

1. 生成した全 docs/ ファイルを読み込む
2. 以下を検出して修正・補完する:
   - **用語の統一**: カテゴリ間で同じものを異なる表記で書いている箇所
   - **矛盾の解消**: 例えば org-profile の用語集とカタログの項目名が一致していない等
   - **情報の補完**: 1つのカテゴリで「要確認」だった事項を他カテゴリの情報で埋められる場合
   - **関連付けの強化**: 設計書 ↔ カタログ ↔ 要件定義書の相互参照を補完
3. 修正・補完した内容を各ファイルに反映する
4. 2周目完了後に全体サマリを報告する

---

## 最終報告

```
## sf-memory 完了

### 実行カテゴリ
- [x] 組織概要・環境情報
- [x] オブジェクト・項目構成
- [x] マスタデータ・自動化
- [x] 設計・機能仕様

### 生成/更新ファイル
（各カテゴリで生成・更新したファイル一覧）

### 主な発見・所見
（業種推定・特筆すべきカスタマイズ・データ傾向・設計上の注意点等）

### 要確認事項（優先度順）
（各カテゴリの「要確認」ハイライト）

### 次のアクション
- docs/ 内の「推定」「要確認」箇所を確認・修正してください
- 必要に応じて sf-retrieve でメタデータを取得してください
- 新機能・項目追加時は該当カテゴリを再実行してください
```
