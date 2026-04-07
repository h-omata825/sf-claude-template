# Salesforce Development OS

Salesforce開発プロジェクトで使うClaude Code設定のテンプレート。

---

## クイックスタート

> **注意**: Git Bash で実行する（コマンドプロンプト・PowerShellでは動作しない）

```bash
curl -sSL https://raw.githubusercontent.com/h-omata825/sf-claude-template/main/scripts/setup.sh | bash -s <フォルダ名> "<作成先パス>"
```

| 引数 | 必須 | 説明 |
|---|---|---|
| `<フォルダ名>` | ✓ | 作成されるフォルダ名。`<作成先パス>/<フォルダ名>/` が生成される |
| `<作成先パス>` | ✓ | 作成先。スペース・日本語を含む場合はダブルクォートで囲む |

実行後:
1. VSCode が自動で開く
2. Claude Code を起動
3. `/setup-sf-project` を実行 → 組織認証（クリック選択式）
4. `/sf-retrieve` を実行 → メタデータ取得
5. `CLAUDE.md` を編集してプロジェクト固有情報を記入
6. `/setup-mcp` を実行 → Backlog・GitHub等のMCP連携を設定

### 既存プロジェクトに参加する場合

```bash
curl -sSL https://raw.githubusercontent.com/h-omata825/sf-claude-template/main/scripts/setup.sh | bash -s <フォルダ名> "<作成先パス>" <プロジェクトリポジトリURL>
```

### 前提条件

- [Salesforce CLI](https://developer.salesforce.com/tools/salesforcecli) がインストール済み
- [Git](https://git-scm.com/) がインストール済み（Git Bash含む）
- [Claude Code](https://claude.ai/code) がインストール済み

---

## フォルダ構成

```
project/
  sfdx-project.json         （sf project generate が生成）
  force-app/main/default/   （sf project generate が生成・Git管理外）
  manifest/                 （sf project generate が生成）
  CLAUDE.md              ← プロジェクト固有ルール（コピー後に編集する）
  README.md              ← このファイル（テンプレートからコピー）
  .gitignore             ← テンプレートからコピー
  .claude/               ← テンプレートからコピー（upgrade.sh で更新）
    CLAUDE.md            ← Salesforce共通ルール
    VERSION              ← テンプレートバージョン
    agents/              ← AIエージェント定義
    commands/            ← スラッシュコマンド定義
    settings.json        ← 権限設定（Git管理対象・チーム共有）
  scripts/               ← シェルスクリプト
    setup.sh             ← 新規プロジェクト作成（curl で直接実行可能）
    setup-sf-project.sh  ← SF組織認証
    setup-mcp.sh         ← MCP連携（.mcp.json）の設定
    upgrade.sh           ← テンプレート更新（差分検出→適用）
    sf-package.sh        ← package.xml 生成・メタデータ取得（/sf-retrieve から呼ばれる）
  docs/                  ← ドキュメント置き場
    requirements/        ← 要件定義書・ユーザーストーリー
    design/              ← 設計書・オブジェクト定義書
    test/                ← テスト計画・テストケース
    minutes/             ← 議事録・決定事項
    manuals/             ← 手順書・マニュアル
```

---

## エージェント（10体）

| エージェント | 担当 |
|---|---|
| `salesforce-dev` | Apex / LWC / Flow 実装、メタデータ設定、デプロイ |
| `maintenance` | 本番障害対応、デバッグログ解析、パフォーマンス調査 |
| `reviewer` | コードレビュー、セキュリティ監査、PRレビュー支援 |
| `qa-engineer` | テスト計画、テストケース作成、UAT支援 |
| `salesforce-architect` | 要件定義、設計書作成・設計レビュー、オブジェクト定義書、影響調査 |
| `project-manager` | タスク管理、スプリント計画、議事録、進捗報告 |
| `doc-writer` | 手順書、マニュアル、リリースノート、資料作成 |
| `data-manager` | データ移行、SOQL最適化、Data Loader、クレンジング |
| `integration-dev` | 外部API連携、REST/SOAP、Platform Events、Named Credentials |
| `assistant` | 調査、メール下書き、翻訳、その他アドホック作業 |

---

## スラッシュコマンド（14個）

| コマンド | 内容 |
|---|---|
| `/setup-sf-project` | Salesforce組織の認証（クリック選択式） |
| `/setup-mcp` | MCP連携の設定（Backlog・GitHub・Slack等） |
| `/sf-retrieve` | package.xml 生成・メタデータ取得 |
| `/upgrade` | テンプレート最新版を取得して更新 |
| `/git-pr` | ブランチ作成・コミット・プッシュ・PR作成 |
| `/sf-implement [内容]` | 機能実装 |
| `/sf-deploy [対象]` | デプロイ前チェック・デプロイ支援 |
| `/sf-review [対象]` | コード・メタデータのレビュー |
| `/sf-debug [症状]` | バグ調査・障害対応 |
| `/sf-analyze [資料]` | 組織解析→資料を自動生成 |
| `/sf-design [内容]` | 機能別設計書の作成 |
| `/sf-catalog` | オブジェクト・項目定義書の自動生成 |
| `/sf-data [内容]` | データ移行・SOQL最適化・クレンジング |
| `/feedback [内容]` | 決定事項・気づきをCLAUDE.mdに記録 |

---

## MCP連携

`/setup-mcp` コマンドで `.mcp.json` を生成・管理する。`.mcp.json` は `.gitignore` 対象（トークンがGitHubに公開されない）。

| MCP | 用途 |
|---|---|
| `backlog` | Backlogチケット管理・課題読み込み |
| `github` | GitHubリポジトリ操作・PRレビュー連携 |
| `slack` | Slackメッセージ送受信 |
| `notion` | Notionページ読み書き |
| `playwright` | ブラウザ操作・UI自動テスト |

---

## テンプレートのアップグレード

プロジェクトフォルダで実行:

```bash
bash scripts/upgrade.sh
```

更新対象: `.claude/`・`scripts/`・`README.md`
更新対象外: `CLAUDE.md`（ルート）・`docs/`・`force-app/`・`.mcp.json`（プロジェクト固有のため触らない）

スクリプトが差分を検出して一覧表示し、確認後に適用する。

---

## ドキュメント

オンボーディング・運用手順・テンプレート説明書は以下で管理している（このリポジトリには含まない）。

| 資料 | 内容 |
|---|---|
| `onboarding.md` | 環境構築から動作確認まで |
| `operations.md` | 日常の開発フロー（保守/新規） |
| `template-guide.md` | エージェント・コマンドの詳細 |
| `project-setup-guide.md` | プロジェクト立ち上げ・Git運用 |

管理場所: `C:\ClaudeCode\docs\sf-template\`

---

## 権限設定（settings.json）

`settings.json` は **Git管理対象**。チーム全員に同じ権限制限が強制される。

### 自動拒否（Claude Codeが実行前にブロック）
- 本番環境へのデプロイ（`*prod*` / `*production*`）
- `rm -rf` / `.claude` の削除
- `.claude/` 配下の編集・書き込み（テンプレート保護）
