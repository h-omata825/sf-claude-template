# テンプレート説明書 — Salesforce Development OS

テンプレートの全機能・構成・使い方のリファレンス。

---

## 目次

1. [テンプレート概要](#1-テンプレート概要)
2. [フォルダ構成](#2-フォルダ構成)
3. [CLAUDE.md の構成](#3-claudemd-の構成)
4. [エージェント（10体）](#4-エージェント10体)
5. [スラッシュコマンド（8個）](#5-スラッシュコマンド8個)
6. [settings.json — 権限設定](#6-settingsjson--権限設定)
7. [MCP連携](#7-mcp連携)
8. [docs/ — プロジェクト資材](#8-docs--プロジェクト資材)
9. [品質ゲート](#9-品質ゲート)

---

## 1. テンプレート概要

### 何ができるか

- Salesforce開発プロジェクトに最適化されたClaude Code環境を即座に構築できる
- 10体の専門エージェントがタスクの種類に応じて自動選択される
- 8個のスラッシュコマンドで頻出タスク（セットアップ・メタデータ取得・ドキュメント自動生成等）を実行できる
- Salesforceのコード品質基準（ガバナ制限・バルク処理・FLS等）が組み込まれており、生成コードの品質が担保される
- 本番デプロイ・テンプレートファイルの変更は自動ブロックされる

### 設計思想

| 思想 | 内容 |
|---|---|
| **共通ルールとプロジェクト固有ルールの分離** | `.claude/CLAUDE.md`（共通・`/upgrade` で配布）と `CLAUDE.md`（プロジェクト固有・管理者が編集）の2層構成 |
| **エージェント自動選択** | ユーザーがエージェントを指定しなくても、タスク内容から自動で最適なエージェントが選ばれる |
| **安全第一** | 本番デプロイ・テンプレートファイルの上書きは自動拒否。人間の確認を必須にしている |
| **Salesforceベストプラクティス組み込み** | ガバナ制限・バルク処理・FLS/CRUD・テストカバレッジの基準がルールとして定義済み |

---

## 2. フォルダ構成

```
project/
├── CLAUDE.md                    ← 【編集する】プロジェクト固有ルール
├── .gitignore                   ← .mcp.json をGit管理外に設定済み
├── .mcp.json                    ← 【.gitignore対象】個人のMCP設定（/setup-mcpで生成）
│
├── .claude/                     ← 【原則触らない】テンプレート共通部分
│   ├── CLAUDE.md                ← 共通ルール・品質基準
│   ├── settings.json            ← 権限設定（Git管理対象・チーム全員に強制）
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
│   └── commands/                ← スラッシュコマンド定義（8個）
│       ├── sf-analyze.md
│       ├── sf-catalog.md
│       ├── sf-design.md
│       ├── sf-data.md
│       ├── sf-package.md
│       ├── setup-sf-project.md
│       ├── setup-mcp.md
│       └── upgrade.md
│
├── docs/                        ← プロジェクト資材
│   ├── overview/                ← 組織プロフィール
│   ├── requirements/            ← 要件定義書
│   ├── design/                  ← 設計書（種別ごとにサブフォルダ）
│   │   ├── apex/
│   │   ├── flow/
│   │   ├── batch/
│   │   ├── lwc/
│   │   ├── integration/
│   │   └── config/
│   ├── catalog/                 ← オブジェクト・項目定義書
│   │   ├── standard/
│   │   └── custom/
│   ├── data/                    ← データ分析・マスタデータ
│   ├── test/                    ← テスト仕様書
│   ├── minutes/                 ← 議事録
│   ├── manuals/                 ← 手順書・マニュアル
│   └── changelog.md             ← 変更履歴（コマンド実行時に自動追記）
│
├── force-app/main/default/      ← Salesforceメタデータ（SFDXが生成）
├── manifest/                    ← package.xml
└── sfdx-project.json
```

### 触っていいファイル / 触らないファイル

| ファイル | 編集 | 説明 |
|---|---|---|
| `CLAUDE.md`（ルート） | **◯ 編集する** | プロジェクト固有情報を記入。`/sync` で共有 |
| `.mcp.json` | **◯ /setup-mcpで生成** | トークン入りMCP設定（.gitignore対象） |
| `docs/` 配下 | **◯ 自由に追加** | プロジェクト資材の蓄積 |
| `force-app/` 配下 | **◯ 開発作業として編集** | Salesforceメタデータ |
| `.claude/CLAUDE.md` | **✕ 触らない** | テンプレートアップグレード時に上書きされる |
| `.claude/agents/` | **✕ 触らない** | テンプレートアップグレード時に上書きされる |
| `.claude/commands/` | **✕ 触らない** | テンプレートアップグレード時に上書きされる |
| `.claude/settings.json` | **✕ 触らない** | Git管理対象。変更はテンプレートリポジトリ側で行う |

---

## 3. CLAUDE.md の構成

### `.claude/CLAUDE.md`（共通ルール）

全プロジェクト共通のルール。テンプレート管理者がメンテする。触らない。

| セクション | 内容 |
|---|---|
| Agent Selection | タスクの種類 → エージェントの対応表 |
| Output Format | 出力形式の統一ルール（コード・ドキュメント・エラー報告等） |
| Security & Permissions | settings.jsonによるブロックとCLAUDE.mdによるルール指示の2層構成 |
| Prohibited Actions | 禁止操作の一覧（本番デプロイ・機密情報出力等） |
| Quality Standards | Salesforceコードの品質基準 |
| Quality Gate | 成果物の自動品質チェック定義 |
| 開発時の振る舞いルール | docs/を参照した精度の高い作業のための指示パターン |

**品質基準の主なルール:**
- ガバナ制限の考慮（SOQL 100回・DML 150回・CPU 10秒等）
- DML / SOQLはループ外に配置（バルク処理必須）
- テストカバレッジ: 75%以上必須、90%以上目標
- FLS / CRUD / 共有設定への配慮（`with sharing` デフォルト）
- ハードコード禁止（カスタムメタデータ / カスタム設定で管理）

### `CLAUDE.md`（プロジェクト固有ルール）

プロジェクトごとに編集するファイル。テンプレートの雛形をベースに記入する。

| セクション | 記入内容 |
|---|---|
| Salesforce組織情報 | org alias（dev / prod等）・環境URL |
| 命名規則 | プレフィックス・命名パターン |
| 権限設計ルール | プロジェクト固有の権限方針 |
| 主要カスタムオブジェクト | オブジェクト名・API名・概要 |
| プロジェクト資材 | docs/配下の資材と生成コマンドの対応（テンプレートに記載済み） |
| 過去の判断・決定事項 | 手動記入またはチャットで「/feedback 〜」と伝えると自動追記 |
| 注意事項・地雷 | 触る前に知っておくべきこと |

### 2つのCLAUDE.mdの優先順位

プロジェクト固有ルール（ルート）が共通ルール（`.claude/`）より優先される。
例: 共通で「テストカバレッジ75%以上」、プロジェクトで「95%以上」と書けば95%が適用される。

---

## 4. エージェント（10体）

タスクの種類に応じて自動で選択されるAI専門家。ユーザーが明示的に指定する必要はない。

| エージェント | 主な担当 |
|---|---|
| **salesforce-dev** | Apex / LWC / Flow実装、メタデータ設定、デプロイ |
| **maintenance** | 本番障害対応、デバッグログ解析、パフォーマンス調査 |
| **reviewer** | コードレビュー（Critical/Warning/Info形式）、設計レビュー、セキュリティ監査 |
| **qa-engineer** | テスト計画・テストケース（UT/IT/ST/UAT）・バグ調査・FLS/権限セキュリティテスト |
| **salesforce-architect** | 要件定義、設計書作成、オブジェクト定義書、影響調査 |
| **project-manager** | タスク管理、スプリント計画、議事録、リリース管理 |
| **doc-writer** | 手順書、マニュアル、報告書、リリースノート |
| **data-manager** | データ移行計画、SOQLチューニング、Data Loader操作 |
| **integration-dev** | 外部API連携（REST/SOAP）、Platform Events、Named Credentials |
| **assistant** | 調査、メール下書き、翻訳、その他アドホック作業 |

### 自動選択の仕組み

`.claude/CLAUDE.md` の「Agent Selection」テーブルに基づいて自動選択される。

```
「取引先トリガーを作って」→ salesforce-dev
「本番でエラーが出てる」  → maintenance
「テスト計画を作って」    → qa-engineer
「このクラスをレビューして」→ reviewer
```

複数エージェントにまたがるタスクはタスクを分解して各エージェントに割り当てる。

---

## 5. スラッシュコマンド（9個）

頻出タスクをワンコマンドで実行するショートカット。`/` + コマンド名 で呼び出す。

| コマンド | 実行エージェント | 概要 |
|---|---|---|
| `/sf-analyze [資料パス]` | salesforce-architect | 接続中の組織を解析し、組織プロフィール・要件定義書を自動生成 |
| `/sf-catalog [オブジェクト名]` | salesforce-architect | オブジェクト・項目定義書を自動生成（引数なし=全量） |
| `/sf-design [内容]` | salesforce-architect | 機能別設計書の作成・既存設計書のインポート |
| `/sf-data [内容]` | data-manager | データ移行計画・マスタデータ資料の作成 |
| `/sf-package [対象]` | salesforce-dev | package.xmlを生成してメタデータを取得（指定/標準セット/全量の3モード） |
| `/git-pr` | — | ブランチ作成・コミット・プッシュ・PR作成を対話形式で実行 |
| `/setup-sf-project` | — | 新規プロジェクトの対話形式セットアップ（フォルダ作成〜組織認証〜メタデータ取得まで） |
| `/setup-mcp` | assistant | MCP連携の設定（新規・更新・削除に対応） |
| `/upgrade [URL] [タグ]` | assistant | テンプレートの最新版を取得し `.claude/` 配下を更新 |

### 各コマンドの補足

#### `/sf-analyze`

組織に接続して以下を自動収集・資料化する:
- カスタムオブジェクト一覧・項目構成、Apexクラス/トリガー一覧、フロー一覧、レコード件数、ユーザー・プロファイル情報等
- 生成ファイル: `docs/overview/org-profile.md`（組織プロフィール）、`docs/requirements/requirements.md`（要件定義書）、`docs/changelog.md`（変更履歴）
- 2回目以降は差分更新モードで動作（手動追記した内容は保持）
- Excel/Word資料を引数に渡すと内容を統合して生成

#### `/sf-catalog`

- 引数なし → 全カスタムオブジェクト + 主要標準オブジェクトの定義書を一括生成
- オブジェクト名指定 → 指定オブジェクトのみ生成
- 既存の定義書（Excel等）を引数に渡すと統合・標準化
- 生成先: `docs/catalog/standard/` または `docs/catalog/custom/`

#### `/sf-package`

メタデータ取得の3モード:
1. **指定する** — クラス名・フロー名等を指定してpackage.xmlを生成
2. **標準セット** — ApexClass・ApexTrigger・Flow・CustomObject・LWC等の開発頻出メタデータを一括取得
3. **全て** — 組織の全メタデータを取得

取得前に `git status` で現在の変更状況を確認（ローカルファイル上書きへの注意）。

#### `/git-pr`

変更内容をブランチにコミット・プッシュし、PRを作成する対話型フロー:

1. `git status` で変更内容を確認
2. ブランチを選択（新規3案提示 / 既存から選択 / カスタム）
3. コミットするファイルを選択
4. コミットメッセージを確認（Conventional Commits形式で自動提案）
5. プッシュ → PR作成（`gh` CLI がある場合は自動作成）

> PR先は `develop` が存在すれば `develop`、なければ `main` を自動選択する。

#### `/upgrade`

更新対象: `.claude/CLAUDE.md`・エージェント・コマンド（追加・更新・削除を検出）
更新対象外: `CLAUDE.md`（ルート）・`docs/`・`force-app/`・`.claude/settings.json`

> settings.jsonはアップグレード対象外。テンプレート側で権限設定が変更された場合は差分を表示するので手動マージする。

---

## 6. settings.json — 権限設定

Claude Codeが実行できる操作の許可・拒否を定義する。**Git管理対象**のため、チーム全員に同じ権限制限が強制される。

### 現在の設定（テスト中モード）

```json
{
  "permissions": {
    "allow": ["Bash(*)"],
    "deny": [
      "Bash(sf project deploy start --target-org *prod*)",
      "Bash(sf project deploy start --target-org *production*)",
      "Bash(rm -rf *)",
      "Bash(rm -r .claude*)",
      "Edit(.claude/CLAUDE.md)",
      "Edit(.claude/agents/*)",
      "Edit(.claude/commands/*)",
      "Edit(.claude/settings.json)",
      "Write(.claude/CLAUDE.md)",
      "Write(.claude/agents/*)",
      "Write(.claude/commands/*)",
      "Write(.claude/settings.json)"
    ]
  }
}
```

### 挙動の説明

| 操作 | 挙動 | 理由 |
|---|---|---|
| 本番org（`*prod*`）へのデプロイ | **自動拒否** | 本番保護 |
| `rm -rf` / `.claude` の削除 | **自動拒否** | 破壊的操作の防止 |
| `.claude/` 配下のファイル編集・書き込み | **自動拒否** | テンプレート保護 |
| Sandbox等へのデプロイ | **自動実行** | denyに該当しない |
| `git push` / `git commit` | **確認ダイアログ** | 現在は確認のみ（後述） |

### Git操作の制限（実運用時に有効化）

`settings.json` の `__pending.git_workflow` に以下が定義されている。
チーム利用開始・PR運用を始める際に `permissions.deny` へ追加して有効化する。

```
"Bash(git push*)"
"Bash(git commit*)"
"Bash(git reset --hard*)"
"Bash(git branch -D*)"
```

### テンプレート保護の仕組み

`.claude/` 配下は `Edit` と `Write` が拒否されている。
- メンバーがClaude Codeで `.claude/` を変更できない
- テンプレートの更新は `/upgrade` コマンド経由のみ
- `settings.json` 自体も保護対象のため、設定の無効化も防止

---

## 7. MCP連携

`/setup-mcp` コマンドで `.mcp.json` を生成・管理する。

### メインMCP

| MCP | 用途 | 優先度 |
|---|---|---|
| **github** | GitHubリポジトリ操作・PRレビュー・Issue管理 | **メイン（推奨）** |

### オプションMCP

| MCP | 用途 |
|---|---|
| slack | Slackメッセージ送受信 |
| gdrive | Google Driveファイルアクセス |
| notion | Notionページ読み書き |
| playwright | ブラウザ操作・UI自動テスト |

### セキュリティ

`.mcp.json` は `.gitignore` 対象のため、トークンがGitHubにpushされることはない。
メンバーは各自 `/setup-mcp` を実行してトークンを設定する。

---

## 8. docs/ — プロジェクト資材

| フォルダ | 内容 | 生成コマンド |
|---|---|---|
| `docs/overview/` | 組織プロフィール（業種推定・データ構成・用語集） | `/sf-analyze` |
| `docs/requirements/` | 要件定義書（AS-IS/TO-BE・機能要件・ビジネスルール） | `/sf-analyze` |
| `docs/design/{種別}/` | 機能別設計書（apex/flow/batch/lwc/integration/config） | `/sf-design` |
| `docs/catalog/standard/` | 標準オブジェクトの項目定義書 | `/sf-catalog` |
| `docs/catalog/custom/` | カスタムオブジェクトの項目定義書 | `/sf-catalog` |
| `docs/data/` | データ移行計画・マスタデータ・データ品質分析 | `/sf-data` |
| `docs/test/` | テスト計画書・テストケース | 手動 |
| `docs/minutes/` | 議事録・決定事項 | 手動 |
| `docs/manuals/` | 手順書・マニュアル | 手動 |
| `docs/changelog.md` | コマンド実行履歴・変更点の記録 | 自動 |

### docs/ がClaude Codeの精度向上に直結する仕組み

`.claude/CLAUDE.md` の「開発時の振る舞いルール」により、Claude Codeは作業前に必ずdocs/を参照する。

```
「項目を作って」と言われたとき
  → docs/catalog/ で既存の項目構成を確認してから作成
  → docs/overview/ の用語集で命名を統一

「Apexを作って」と言われたとき
  → docs/design/apex/ で設計書を確認してから実装
  → docs/requirements/ でビジネスルールを確認
```

docs/が充実するほど、Claude Codeがプロジェクト文脈を把握した精度の高いコードを生成する。

---

## 9. 品質ゲート

コード実装・設計書作成などの成果物は、完了前に自動でレビューエージェントの基準でチェックを実行する。

| 作業 | チェック担当 |
|---|---|
| Apex / LWC / Flow 実装 | reviewer エージェント |
| テストクラス作成 | qa-engineer エージェント |
| 設計書・要件定義書 | reviewer エージェント |
| データ移行・SOQL | reviewer エージェント |

問題があれば修正案を提示。ユーザーが「スキップ」と言えば省略可能。
