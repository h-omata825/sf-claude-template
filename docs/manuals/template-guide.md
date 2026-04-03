# テンプレート説明書 — Salesforce Development OS

テンプレートの全機能・構成要素・使い方のリファレンス。

---

## 目次

1. [テンプレート概要](#1-テンプレート概要)
2. [フォルダ構成](#2-フォルダ構成)
3. [CLAUDE.md — ルールファイル](#3-claudemd--ルールファイル)
4. [エージェント（10体）](#4-エージェント10体)
5. [スラッシュコマンド（7個）](#5-スラッシュコマンド7個)
6. [settings.json — 権限設定](#6-settingsjson--権限設定)
7. [.mcp.json — 外部ツール連携](#7-mcpjson--外部ツール連携)
8. [docs/ — プロジェクト資材](#8-docs--プロジェクト資材)
9. [setup.sh / setup-sf-project — セットアップ](#9-setupsh--setup-sf-project--セットアップ)
10. [.gitignore](#10-gitignore)
11. [Claude Codeの基本操作](#11-claude-codeの基本操作)
12. [活用パターン・Tips](#12-活用パターンtips)

---

## 1. テンプレート概要

### 何ができるか

- Salesforce開発プロジェクトに最適化されたClaude Code環境を即座に構築できる
- 10体の専門エージェントがタスクの種類に応じて自動選択される
- 6つのスラッシュコマンドで頻出タスクをワンコマンドで実行できる
- 品質基準（ガバナ制限・バルク処理・FLS等）が組み込まれており、生成コードの品質が担保される
- 本番デプロイ等の危険な操作は自動ブロックされる

### 設計思想

| 思想 | 内容 |
|---|---|
| **共通ルールとプロジェクト固有ルールの分離** | `.claude/CLAUDE.md`（共通・触らない）と `CLAUDE.md`（プロジェクト固有・自由に編集）の2層構成 |
| **エージェント自動選択** | ユーザーがエージェントを指定しなくても、タスク内容から自動で最適なエージェントが選ばれる |
| **安全第一** | 本番デプロイ・git push・機密情報の出力は自動拒否。人間の確認を必須にしている |
| **Salesforceベストプラクティス組み込み** | ガバナ制限・バルク処理・FLS/CRUD・テストカバレッジの基準がルールとして定義済み |

---

## 2. フォルダ構成

```
project/
├── CLAUDE.md                    ← 【編集する】プロジェクト固有ルール
├── .gitignore                   ← Git除外設定
├── .mcp.json                    ← 外部ツール連携設定（トークンは各自設定）
│
├── .claude/                     ← 【原則触らない】テンプレート共通部分
│   ├── CLAUDE.md                ← 共通ルール・品質基準
│   ├── settings.json            ← 権限設定（自動許可・自動拒否）
│   ├── agents/                  ← エージェント定義（10体）
│   │   ├── salesforce-dev.md
│   │   ├── maintenance.md
│   │   ├── reviewer.md
│   │   ├── qa-engineer.md
│   │   ├── salesforce-architect.md
│   │   ├── project-manager.md
│   │   ├── doc-writer.md
│   │   ├── data-manager.md
│   │   ├── integration-dev.md
│   │   └── assistant.md
│   └── commands/                ← スラッシュコマンド定義（7個）
│       ├── sf-implement.md
│       ├── sf-deploy.md
│       ├── sf-review.md
│       ├── sf-debug.md
│       ├── sf-analyze.md
│       ├── feedback.md
│       └── save-doc.md
│
├── docs/                        ← プロジェクト資材
│   ├── overview/                ← 組織プロフィール
│   ├── requirements/            ← 要件定義書
│   ├── design/                  ← 設計書
│   ├── catalog/                 ← オブジェクト・項目定義書
│   ├── data/                    ← データ分析
│   ├── test/                    ← テスト仕様
│   ├── minutes/                 ← 議事録
│   ├── manuals/                 ← 手順書・マニュアル
│   └── changelog.md             ← 変更履歴（自動追記）
│
├── force-app/main/default/      ← Salesforceメタデータ（SFDXが生成）
├── manifest/                    ← package.xml（SFDXが生成）
└── sfdx-project.json            ← SFDXプロジェクト設定（SFDXが生成）
```

### 触っていいファイル / 触らないファイル

| ファイル | 編集 | 説明 |
|---|---|---|
| `CLAUDE.md`（ルート） | **◯ 編集する** | プロジェクト情報・命名規則・決定事項を記入 |
| `.mcp.json` | **◯ トークン設定** | 使用するMCPのトークンを設定 |
| `docs/` 配下 | **◯ 自由に追加** | プロジェクト資材の蓄積 |
| `.claude/CLAUDE.md` | **✕ 触らない** | テンプレートアップグレード時に上書きされる |
| `.claude/agents/` | **✕ 触らない** | テンプレートアップグレード時に上書きされる |
| `.claude/commands/` | **✕ 触らない** | テンプレートアップグレード時に上書きされる |
| `.claude/settings.json` | **△ 慎重に** | 個人設定を追加する場合のみ。`.gitignore` 対象 |

---

## 3. CLAUDE.md — ルールファイル

Claude Codeの振る舞いを制御する最も重要なファイル。プロジェクトフォルダを開いたときに自動で読み込まれる。

### `.claude/CLAUDE.md`（共通ルール）

全プロジェクト共通のルール。テンプレート管理者がメンテする。

**含まれる内容:**

| セクション | 内容 |
|---|---|
| Agent Selection | タスクの種類 → エージェントの対応表 |
| Output Format | 出力形式の統一ルール（コード・ドキュメント・エラー報告等） |
| Prohibited Actions | 禁止操作の一覧（本番デプロイ・git push・機密情報出力等） |
| Quality Standards | Salesforceコードの品質基準 |
| プロジェクト資材の参照 | docs/配下のフォルダ構成と用途 |

**品質基準の主なルール:**
- ガバナ制限の考慮（SOQL 100回・DML 150回・CPU 10秒等）
- DML / SOQLはループ外に配置（バルク処理必須）
- テストカバレッジ: 75%以上必須、90%以上目標
- FLS / CRUD / 共有設定への配慮（`with sharing` デフォルト）
- ハードコード禁止（カスタムメタデータ / カスタム設定で管理）

### `CLAUDE.md`（プロジェクト固有ルール）

プロジェクトごとに編集するファイル。

**記入すべき内容:**

| セクション | 記入内容 | 例 |
|---|---|---|
| Salesforce組織情報 | org alias、環境URL | `project-dev`, `project-prod` |
| 命名規則 | プレフィックス、命名パターン | `PROJ_Order__c`, `PROJOrderService` |
| 権限設計ルール | プロジェクト固有の権限方針 | 「標準プロファイルは編集禁止」 |
| 主要カスタムオブジェクト | オブジェクト名・API名・概要 | |
| プロジェクト資材 | 資材の場所・コマンド | 自動生成済みのため確認のみ |
| 過去の判断・決定事項 | `/feedback` で自動追記 or 手動記入 | 「受注はOpportunityを流用」 |
| 注意事項・地雷 | ハマりポイント、競合情報 | 「Accountトリガーは○○と競合」 |

### 2つのCLAUDE.mdの優先順位

```
1. CLAUDE.md（ルート・プロジェクト固有）  ← 優先
2. .claude/CLAUDE.md（共通ルール）         ← ベース
```

プロジェクト固有ルールが共通ルールと矛盾する場合、プロジェクト固有ルールが優先される。
例: 共通ルールで「テストカバレッジ75%以上」だが、プロジェクトで「95%以上」と記載すれば95%が適用される。

---

## 4. エージェント（10体）

タスクの種類に応じて自動で選択されるAI専門家。ユーザーが明示的に指定する必要はない（自然言語で依頼すれば自動選択される）。

### 一覧

| # | エージェント | 主な担当 | 使用ツール |
|---|---|---|---|
| 1 | **salesforce-dev** | Apex / LWC / Flow実装、メタデータ設定、デプロイ | Read, Edit, Write, Glob, Grep, Bash, TodoWrite |
| 2 | **maintenance** | 本番障害対応、デバッグログ解析、パフォーマンス調査 | Read, Edit, Write, Glob, Grep, Bash, TodoWrite |
| 3 | **reviewer** | コードレビュー、設計レビュー、セキュリティ監査 | Read, Glob, Grep, Bash, TodoWrite |
| 4 | **qa-engineer** | テスト計画、テストケース作成、UAT支援、品質確認 | Read, Glob, Grep, Bash, TodoWrite |
| 5 | **salesforce-architect** | 要件定義、設計書作成、オブジェクト定義書、影響調査 | Read, Edit, Write, Glob, Grep, Bash, TodoWrite |
| 6 | **project-manager** | タスク管理、スプリント計画、議事録、進捗報告、リリース管理 | Read, Edit, Write, Glob, Grep, Bash, TodoWrite |
| 7 | **doc-writer** | 手順書、マニュアル、報告書、リリースノート、MD変換 | Read, Edit, Write, Glob, Grep, Bash, TodoWrite |
| 8 | **data-manager** | データ移行、SOQL最適化、Data Loader、クレンジング | Read, Edit, Write, Glob, Grep, Bash, TodoWrite |
| 9 | **integration-dev** | 外部API連携、REST/SOAP、Platform Events、Named Credentials | Read, Edit, Write, Glob, Grep, Bash, TodoWrite |
| 10 | **assistant** | 調査、メール下書き、翻訳、その他アドホック作業 | Read, Edit, Write, Glob, Grep, Bash |

### 各エージェントの詳細

#### 1. salesforce-dev（Salesforce開発者）

**最も使用頻度が高いエージェント。** Salesforceの実装全般を担当する。

対応範囲:
- **Apex**: クラス・トリガー・バッチ・Queueable・Schedulable・テストクラス
- **LWC**: コンポーネント・JSコントローラー・HTML・CSS・@wire・カスタムイベント
- **Flow**: 画面フロー・自動起動フロー・スケジュールフロー・レコードトリガーフロー
- **メタデータ設定**: オブジェクト・項目・レイアウト・権限セット・入力規則・レポート等
- **SF CLI操作**: メタデータ取得・デプロイ・テスト実行
- **マニフェスト**: package.xml・destructiveChanges.xml作成

自動的に守られるルール:
- バルク処理パターン（DML/SOQLはループ外）
- `with sharing` デフォルト
- FLS/CRUDチェック
- テストクラスのセット提供（正常系・異常系・バルク200件）
- Before/After形式でのコード提示

呼び出し例:
```
Account更新時に関連Contactのメールアドレスを同期するトリガーを作って
```
```
/sf-implement 商談クローズ時にPDFを生成してメール送信するバッチ
```

#### 2. maintenance（保守運用エンジニア）

本番障害やパフォーマンス問題の調査・対応に特化。

対応範囲:
- 障害トリアージ（影響範囲特定・重大度判定）
- Apexデバッグログ解析・スタックトレース読み解き
- ガバナ制限エラーの分析・修正
- パフォーマンス問題（SOQL最適化・CPU時間削減）
- 障害報告書作成（影響→原因→暫定対応→恒久対応→再発防止）

呼び出し例:
```
/sf-debug 商談の一括更新で「Too many SOQL queries」エラーが出る
```
```
このデバッグログを解析して原因を特定して（ログを貼り付け）
```

#### 3. reviewer（レビュアー）

コードレビュー・設計レビュー・セキュリティ監査を担当。

レビュー観点:
- **Critical**: ループ内SOQL/DML、FLS未チェック、SOQLインジェクション、ハードコードID
- **Warning**: エラーハンドリング不足、テストカバレッジ不足、可読性
- **Info**: 改善提案、ベストプラクティス

出力形式:
```
Critical X件 / Warning X件 / Info X件
マージ可否: OK / 要修正
```

呼び出し例:
```
/sf-review force-app/main/default/classes/OrderService.cls
```
```
このPRの変更内容をレビューして
```

#### 4. qa-engineer（QAエンジニア）

テスト計画・テストケース作成・バグ調査を担当。

対応範囲:
- テスト計画書の作成
- テストケース作成（正常系・異常系・境界値・バルク）
- バグの根本原因分析
- UAT支援（ユーザー受入テストのシナリオ作成）
- Apexテストクラスのレビュー

呼び出し例:
```
OrderServiceクラスのテスト計画を作成して
```
```
受注フローのUATシナリオを作って
```

#### 5. salesforce-architect（アーキテクト）

要件定義・設計・上流工程を担当。`/sf-analyze` コマンドの実行エンジン。

対応範囲:
- Salesforce組織の解析・プロフィール生成
- 要件定義書の自動生成（AS-IS / TO-BE）
- オブジェクト設計・データモデル設計
- 影響調査（変更による影響範囲の特定）
- ユーザーストーリー作成

呼び出し例:
```
/sf-analyze
```
```
受注管理機能の設計書を作って
```

#### 6. project-manager（プロジェクトマネージャー）

タスク管理・計画・記録を担当。

対応範囲:
- タスク分解・WBS作成
- スプリント計画
- 議事録整理（決定事項・アクションアイテム抽出）
- 進捗報告書作成
- リリース計画・デプロイ計画
- package.xml作成・リリース判定

呼び出し例:
```
この会議メモから議事録を作って（メモを貼り付け）
```
```
次スプリントのタスクを洗い出して
```

#### 7. doc-writer（ドキュメントライター）

資料作成・ドキュメント整備を担当。

対応範囲:
- 手順書・マニュアル作成
- 提案書・報告書作成
- リリースノート作成
- Excel/PowerPoint → Markdown変換
- 議事録の清書

呼び出し例:
```
/save-doc（資料を貼り付け）
```
```
データ移行手順書を作って
```

#### 8. data-manager（データ管理者）

データ移行・データ品質管理を担当。

対応範囲:
- データ移行計画の策定
- CSVマッピング定義書の作成
- Data Loader操作手順
- SOQL最適化・大量データ対応
- データクレンジング（重複排除・正規化）

呼び出し例:
```
旧システムからAccountとContactを移行するマッピング定義を作って
```
```
このCSVのデータクレンジング計画を立てて
```

#### 9. integration-dev（連携開発者）

外部システム連携の実装・設計を担当。

対応範囲:
- REST / SOAP APIコールアウト実装
- Named Credentials設定
- External Services設定
- Platform Events（イベント駆動連携）
- Outbound Messages
- MuleSoft/middleware連携設計

呼び出し例:
```
外部在庫管理APIとREST連携するApexクラスを作って
```
```
受注確定時にPlatform Eventを発行する設計をして
```

#### 10. assistant（汎用アシスタント）

上記エージェントの対象外となる一般業務を担当。

対応範囲:
- 調査・情報収集
- メール下書き・Slack文面作成
- 翻訳
- その他アドホックな依頼

呼び出し例:
```
Salesforce Winter '26の新機能をまとめて
```
```
この英語のリリースノートを日本語に翻訳して
```

### エージェントの自動選択の仕組み

`.claude/CLAUDE.md` の「Agent Selection」テーブルに基づいて、ユーザーの入力内容からClaude Codeが最適なエージェントを自動選択する。

```
ユーザー: 「Accountトリガーを作って」
  → salesforce-dev が選択される

ユーザー: 「本番でエラーが出てる」
  → maintenance が選択される

ユーザー: 「このクラスをレビューして」
  → reviewer が選択される
```

複数エージェントにまたがるタスクの場合:
```
ユーザー: 「トリガーを実装してレビューもして」
  → salesforce-dev で実装 → reviewer でレビュー（順番に実行）
```

---

## 5. スラッシュコマンド（7個）

頻出タスクをワンコマンドで実行するショートカット。`/` + コマンド名 で呼び出す。

### 一覧

| コマンド | 引数 | 実行エージェント | 概要 |
|---|---|---|---|
| `/sf-implement` | 実装内容 | salesforce-dev | 機能実装（要件確認→設計→実装→テスト→デプロイ情報） |
| `/sf-deploy` | デプロイ対象・環境 | salesforce-dev | デプロイ前チェック・デプロイ支援 |
| `/sf-review` | レビュー対象 | reviewer | コード・メタデータのレビュー |
| `/sf-debug` | 症状・エラー内容 | maintenance | バグ調査・障害対応 |
| `/sf-analyze` | (任意)資料パス | salesforce-architect | 組織解析→プロフィール・要件定義書を自動生成 |
| `/feedback` | 内容 | assistant | 決定事項・気づきをCLAUDE.mdに記録 |
| `/save-doc` | (資料を貼り付け) | doc-writer | 資料をMarkdownに変換してdocs/に保存 |

### 各コマンドの詳細

#### `/sf-implement [実装内容]`

機能実装のフルサイクルを実行する。

```
/sf-implement Account更新時に関連ContactのMailingAddressを同期するトリガー
```

実行される手順:
1. 要件確認（スコープ・影響オブジェクト特定）
2. 設計確認（`docs/design/` の関連資料参照）
3. 実装（Before/After形式で提示）
4. テストクラス作成（正常系・異常系・バルク200件）
5. デプロイ情報（package.xmlへの追加コンポーネント、手動設定作業の提示）

#### `/sf-deploy [対象・環境]`

デプロイ前チェックとデプロイ支援を行う。

```
/sf-deploy manifest/package.xml を dev環境にデプロイ
```

**重要**: 本番環境へのデプロイは `settings.json` で自動拒否されるため、必ず人間の確認が入る。

#### `/sf-review [対象]`

コード・メタデータのレビューを実行する。

```
/sf-review force-app/main/default/classes/OrderService.cls
/sf-review force-app/main/default/triggers/
```

出力形式:
- Critical（必ず修正）→ Warning（修正推奨）→ Info（提案）の3段階
- 各指摘に理由と具体的な修正コードを添付
- 総評とマージ可否判定

#### `/sf-debug [症状]`

バグ調査・障害対応を実行する。

```
/sf-debug 商談の一括更新でSystem.LimitExceptionが発生
/sf-debug （デバッグログを貼り付け）
```

実行される手順:
1. 影響確認（重大度判定）
2. ログ解析（エラー箇所の特定）
3. 原因分析
4. 暫定対応の提案
5. 恒久対応の実装

#### `/sf-analyze [資料パス]`

Salesforce組織を解析し、組織プロフィールと要件定義書を自動生成する。

```
/sf-analyze
/sf-analyze docs/requirements/ヒアリングメモ.md
/sf-analyze C:/Users/xxx/Desktop/企画書.xlsx
```

生成ファイル:
- `docs/overview/org-profile.md` — 組織プロフィール（業種推定・データ構成・技術的所見）
- `docs/requirements/requirements.md` — 要件定義書（AS-IS/TO-BE・機能要件・非機能要件）
- `docs/changelog.md` — 変更履歴（追記）

2回目以降は差分更新モードで動作し、変更点のみを更新する。

#### `/feedback [内容]`

決定事項・気づき・注意事項をCLAUDE.mdに記録する。

```
/feedback 受注オブジェクトはOpportunityを流用する。新規オブジェクトは作らない
/feedback AccountトリガーはXXXパッケージと競合するため、条件チェックが必要
```

記録先: `CLAUDE.md` の「過去の判断・決定事項」または「注意事項・地雷」セクション

#### `/save-doc`

添付・貼り付けされた資料をMarkdownに変換してdocs/に保存する。

```
/save-doc
（要件定義書のExcelを貼り付け or ファイルパスを指定）
```

処理:
1. 資料の内容からカテゴリを自動判定（requirements / design / test / minutes / manuals）
2. ファイル名を自動生成（`YYYYMMDD_<タイトル>.md`）
3. Markdown形式に変換して保存
4. 保存パスを報告

---

## 6. settings.json — 権限設定

Claude Codeが実行できる操作の許可・拒否を定義する。

### 現在の設定

```json
{
  "permissions": {
    "allow": [
      "Bash(*)"           // 全Bashコマンドを自動許可
    ],
    "deny": [
      // 本番デプロイを自動拒否
      "Bash(sf project deploy start --target-org *prod*)",
      "Bash(sf project deploy start --target-org *production*)",
      // Git操作を自動拒否
      "Bash(git push*)",
      "Bash(git commit*)",
      // 破壊的操作を自動拒否
      "Bash(git reset --hard*)"
    ]
  }
}
```

### 挙動の説明

| 操作 | 挙動 |
|---|---|
| `sf project deploy start --target-org dev` | **自動実行** （devはdenyに該当しない） |
| `sf project deploy start --target-org prod` | **自動拒否** （prodがdenyにマッチ） |
| `git push origin feature/xxx` | **自動拒否** （git push*にマッチ） |
| `git commit -m "..."` | **自動拒否** （git commit*にマッチ） |
| `sf apex run test ...` | **自動実行** （allowのBash(*)にマッチ） |

### カスタマイズ

追加の許可・拒否ルールが必要な場合は `settings.json` を編集する。

> **注意**: `.claude/settings.json` は `.gitignore` に含まれるため、個人設定としてGit管理対象外。チームで共有したい設定変更はテンプレート管理者に依頼する。

---

## 7. .mcp.json — 外部ツール連携

MCP（Model Context Protocol）サーバーを通じて外部ツールと連携する設定。

### 利用可能なMCP

| MCP | 用途 | デフォルト状態 |
|---|---|---|
| **github** | GitHubリポジトリ操作・PRレビュー | 無効 |
| **slack** | Slackメッセージ送受信 | 無効 |
| **google-drive** | Google Driveファイルアクセス | 無効 |
| **notion** | Notionページ読み書き | 無効 |
| **playwright** | ブラウザ操作・UI自動テスト | 無効 |

### 有効化手順

1. `.mcp.json` を開く
2. 有効にしたいサーバーの `"disabled": true` の行を削除
3. `<YOUR_TOKEN>` を実際のトークンに置換
4. Claude Codeを再起動

例（GitHub MCPの有効化）:

Before:
```json
"github": {
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-github"],
  "env": {
    "GITHUB_PERSONAL_ACCESS_TOKEN": "<YOUR_TOKEN>"
  },
  "disabled": true
}
```

After:
```json
"github": {
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-github"],
  "env": {
    "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_xxxxxxxxxxxxxxxxxxxx"
  }
}
```

### セキュリティ上の注意

- `.mcp.json` はGit管理されるファイル。トークンを直接書くとリポジトリに公開される可能性がある
- 推奨: 環境変数を使う（`$GITHUB_TOKEN` のように参照）
- またはチームで `.mcp.json` を `.gitignore` に追加する運用を検討

---

## 8. docs/ — プロジェクト資材

プロジェクトのドキュメントを格納するフォルダ。

### フォルダ構成と用途

| フォルダ | 内容 | 自動生成 | 手動作成 |
|---|---|---|---|
| `docs/overview/` | 組織プロフィール | `/sf-analyze` | - |
| `docs/requirements/` | 要件定義書・ヒアリングメモ | `/sf-analyze` | ◯ |
| `docs/design/` | 設計書・オブジェクト定義書 | — | ◯ |
| `docs/catalog/` | オブジェクト・項目定義書 | — | ◯ |
| `docs/data/` | データ分析・移行計画 | — | ◯ |
| `docs/test/` | テスト計画・テストケース | — | ◯ |
| `docs/minutes/` | 議事録・決定事項 | — | ◯ |
| `docs/manuals/` | 手順書・マニュアル | — | ◯ |
| `docs/changelog.md` | 変更履歴 | 自動追記 | ◯ |

### docs/にドキュメントを追加する方法

1. **コマンドで自動生成**: `/sf-analyze`, `/save-doc` 等
2. **Claude Codeに依頼**: 「テスト計画書を作って」→ qa-engineerが `docs/test/` に作成
3. **手動で作成**: Markdownファイルを直接追加

### なぜdocs/にドキュメントを置くのか

Claude Codeは `CLAUDE.md` の「プロジェクト資材の参照」セクションを通じて `docs/` 配下のドキュメントを参照する。ここにドキュメントを置くことで:
- 実装時に設計書を自動参照してくれる
- レビュー時に要件と照合してくれる
- 矛盾や不整合を検出してくれる

---

## 9. setup.sh / setup-sf-project — セットアップ

### setup.sh（シェルスクリプト）

コマンドラインからプロジェクトを作成するスクリプト。

```bash
bash setup.sh <プロジェクト名> [作成先パス]
```

実行内容:
1. `sf project generate` でSFDXプロジェクトを作成
2. テンプレートファイル（`.claude/`, `CLAUDE.md`, `docs/`, `.mcp.json`）をコピー
3. `.gitignore` に `.claude/settings.json` を追加

### /setup-sf-project（スラッシュコマンド）

Claude Code内から対話形式でプロジェクトを作成するコマンド。

```
/setup-sf-project
```

対話で聞かれる内容:
1. プロジェクトのフォルダ名
2. 作成先パス
3. テンプレートのGitリポジトリURL（デフォルトあり）
4. Salesforce組織の認証情報

setup.shと比べて以下が追加:
- テンプレートのGit clone対応
- Salesforce組織認証の対話支援
- メタデータ取得のオプション
- VSCodeでプロジェクトフォルダを自動オープン

---

## 10. .gitignore

```
# Salesforce CLI
.sfdx/
.sf/

# VSCode
.vscode/

# ログ
*.log

# OS
.DS_Store
Thumbs.db

# データ（機密情報を含む可能性）
data/*.csv
data/*.json

# 環境設定
.env
*.env.*

# Node modules
node_modules/

# Apex test results
test-results/

# Claude Code（個人設定）— setup時に追記
.claude/settings.json
```

---

## 11. Claude Codeの基本操作

### 起動方法

- **VSCode拡張**: サイドバーのClaude Codeアイコン or `Ctrl+Shift+P` → "Claude Code"
- **CLI**: ターミナルで `claude` を実行

### 基本的な使い方

| やりたいこと | 入力例 |
|---|---|
| 自然言語で依頼 | 「Accountの更新トリガーを作って」 |
| スラッシュコマンド | `/sf-implement 商談クローズ時のメール通知` |
| ファイルを指定して依頼 | 「このファイルをレビューして」+ ファイルを開いた状態 |
| 資料を読み込ませる | 「この要件書に基づいて設計して」+ ファイルパスを指定 |

### 知っておくと便利な操作

| 操作 | 説明 |
|---|---|
| `/` + コマンド名 | スラッシュコマンドの実行 |
| ファイルを開いた状態で依頼 | 開いているファイルがコンテキストに含まれる |
| パスを指定して依頼 | 「`force-app/main/default/classes/` のクラスをレビューして」 |
| 「docs/を確認して」 | プロジェクト資材を参照した上で回答してくれる |

---

## 12. 活用パターン・Tips

### パターン1: プロジェクト立ち上げ

```
1. /setup-sf-project でプロジェクト作成
2. /sf-analyze で組織解析・要件定義書の自動生成
3. 生成されたドキュメントをレビュー・修正
4. CLAUDE.md にプロジェクト固有情報を記入
```

### パターン2: 日常の開発サイクル

```
1. /sf-implement で機能実装
2. /sf-review でセルフレビュー
3. 指摘事項を修正
4. /sf-deploy で検証環境にデプロイ
```

### パターン3: 障害対応

```
1. /sf-debug でエラー内容を貼り付け
2. 原因特定 → 暫定対応を実施
3. 恒久対応を /sf-implement で実装
4. /feedback で「地雷」として記録
```

### パターン4: ドキュメント整備

```
1. 会議メモを貼り付けて「議事録にして」→ project-manager が整理
2. /save-doc で docs/minutes/ に保存
3. 決定事項は /feedback で CLAUDE.md にも記録
```

### パターン5: 引き継ぎ・新規参加者

```
1. /sf-analyze で最新の組織状態を更新
2. 新メンバーは CLAUDE.md と docs/ を一読
3. 「プロジェクトの概要を教えて」と聞くだけで、CLAUDE.md + docs/ の内容を踏まえた回答が得られる
```

### Tips

| Tip | 説明 |
|---|---|
| **CLAUDE.mdを育てる** | `/feedback` で決定事項・注意事項を積極的に記録する。CLAUDE.mdが充実するほどClaude Codeの回答精度が上がる |
| **docs/を充実させる** | 要件書・設計書をdocs/に置くほど、実装時の自動参照精度が上がる |
| **レビューを習慣化** | `/sf-review` をコミット前に必ず実行する。Critical指摘がゼロになるまで修正 |
| **エージェントを意識しない** | 自然言語で依頼すれば最適なエージェントが自動選択される。明示的に指定する必要はほぼない |
| **Before/After形式** | コード変更は必ずBefore/After形式で提示されるため、差分が明確 |

---

## 付録: よくある質問（FAQ）

### Q: エージェントを手動で指定する方法は？
A: 通常は不要（自動選択される）。どうしても指定したい場合は「reviewerエージェントとして、XXXをレビューして」のように依頼する。

### Q: 新しいエージェントを追加できる？
A: `.claude/agents/` にMarkdownファイルを追加し、`.claude/CLAUDE.md` の「Agent Selection」テーブルに行を追加する。ただしテンプレートアップグレード時に上書きされるため、テンプレートリポジトリ側で追加するのが推奨。

### Q: 新しいスラッシュコマンドを追加できる？
A: `.claude/commands/` にMarkdownファイルを追加する。ファイル名がコマンド名になる（例: `sf-test.md` → `/sf-test`）。エージェントと同様、テンプレート側での管理を推奨。

### Q: CLAUDE.mdに何を書けばいいかわからない
A: まずは最低限の「Salesforce組織情報」と「命名規則」だけ記入すれば使い始められる。運用しながら `/feedback` で徐々に充実させていく。

### Q: テンプレートを別のプロジェクト（非Salesforce）に応用できる？
A: `.claude/` 配下のエージェント・コマンド・共通ルールをそのプロジェクト向けに書き換えれば応用可能。フォルダ構成の思想（共通ルール + プロジェクト固有ルールの2層構成）は汎用的。

### Q: MCPを全部有効にしていいか？
A: 必要なものだけ有効にする。不要なMCPを有効にするとClaude Codeの起動が遅くなる可能性がある。また、トークン管理の手間も増える。
