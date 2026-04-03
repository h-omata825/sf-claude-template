# Salesforce Development OS

Salesforce開発プロジェクトで使うClaude Code設定のテンプレート。
このフォルダをプロジェクト用にコピーして使う。

---

## テンプレートの使い方

### 方法1: セットアップコマンド（推奨）

Claude Codeで `/setup-sf-project` を実行すると、対話形式でプロジェクトを作成できる。

### 方法2: setup.sh（CLI）

```bash
bash setup.sh <プロジェクト名> [出力先]
# 例: bash setup.sh myProject C:/workspace
```

### 方法3: 手動セットアップ

1. SFDXプロジェクトを作成: `sf project generate --name . --manifest`
2. テンプレートの `.claude/`, `CLAUDE.md`, `docs/`, `upgrade.sh` をコピー
3. `CLAUDE.md` をプロジェクト固有の情報に書き換える
4. `/setup-mcp` でMCP連携を設定（必要な場合）
5. SF CLIで組織に認証

---

## フォルダ構成

```
project/                    ← sf project generate で生成されたSFDXプロジェクト
  sfdx-project.json         （SFDXが生成）
  force-app/main/default/   （SFDXが生成）
  manifest/                 （SFDXが生成）
  CLAUDE.md              ← プロジェクト固有ルール（コピー後に編集する）
  .gitignore             ← テンプレートからコピー
  upgrade.sh             ← テンプレートアップグレード用スクリプト
  .claude/               ← テンプレートからコピー（中身は触らない）
    CLAUDE.md            ← Salesforce共通ルール
    agents/              ← AIエージェント定義（10体）
    commands/            ← スラッシュコマンド定義（10個）
    settings.json        ← 権限設定（.gitignore対象）
  docs/                  ← テンプレートからコピー
    requirements/        ← 要件定義書・ユーザーストーリー
    design/              ← 設計書・オブジェクト定義書
    test/                ← テスト計画・テストケース
    minutes/             ← 議事録・決定事項
    manuals/             ← 手順書・マニュアル
```

---

## エージェント（10体）

タスクの種類に応じて自動的に適切なエージェントが選択される。

| エージェント | 担当 |
|---|---|
| `salesforce-dev` | Apex / LWC / Flow 実装、メタデータ設定、デプロイ |
| `maintenance` | 本番障害対応、デバッグログ解析、パフォーマンス調査 |
| `reviewer` | コードレビュー、設計レビュー、セキュリティ監査 |
| `qa-engineer` | テスト計画、テストケース作成、UAT支援 |
| `salesforce-architect` | 要件定義、設計書・オブジェクト定義書作成、影響調査 |
| `project-manager` | タスク管理、スプリント計画、議事録、進捗報告 |
| `doc-writer` | 手順書、マニュアル、リリースノート、資料作成 |
| `data-manager` | データ移行、SOQL最適化、Data Loader、クレンジング |
| `integration-dev` | 外部API連携、REST/SOAP、Platform Events、Named Credentials |
| `assistant` | 調査、メール下書き、翻訳、その他アドホック作業 |

---

## スラッシュコマンド（10個）

| コマンド | 内容 | エージェント |
|---|---|---|
| `/sf-implement [内容]` | 機能実装 | salesforce-dev |
| `/sf-deploy [対象]` | デプロイ前チェック・デプロイ支援 | salesforce-dev |
| `/sf-review [対象]` | コード・メタデータのレビュー | reviewer |
| `/sf-debug [症状]` | バグ調査・障害対応 | maintenance |
| `/sf-analyze [資料]` | 組織解析→プロフィール・要件定義書を自動生成 | salesforce-architect |
| `/sf-design [内容]` | 機能別設計書の作成・既存設計書のインポート | salesforce-architect |
| `/sf-catalog` | オブジェクト・項目定義書の自動生成 | salesforce-architect |
| `/feedback [内容]` | 決定事項・気づきをCLAUDE.mdに記録 | assistant |
| `/save-doc` | 添付資料をMarkdownに変換してdocsに保存 | doc-writer |
| `/setup-mcp` | MCP連携の設定（新規作成・更新・削除に対応） | assistant |

---

## 権限設定（settings.json）

### 自動許可
- すべてのBashコマンドを自動許可（`Bash(*)`）

### 自動拒否（確認なしに実行しない）
- 本番環境へのデプロイ（`*prod*` / `*production*`）
- `git push` / `git commit`
- `git reset --hard`

---

## MCP連携

`/setup-mcp` コマンドで `.mcp.json` を生成・管理する。

- **新規**: `/setup-mcp` → 使うMCPを選択 → トークン入力 → `.mcp.json` 生成
- **更新**: `/setup-mcp` → 追加・変更・削除を選択
- `.mcp.json` は `.gitignore` 対象（トークンがGitHubに公開されない）

| MCP | 用途 |
|---|---|
| `github` | GitHubリポジトリ操作・PRレビュー連携 |
| `slack` | Slackメッセージ送受信 |
| `gdrive` | Google Driveファイルアクセス |
| `notion` | Notionページ読み書き |
| `playwright` | ブラウザ操作・UI自動テスト |

---

## テンプレートのアップグレード

テンプレートに更新があった場合、プロジェクトフォルダで以下を実行:

```bash
bash upgrade.sh
# or
bash upgrade.sh <テンプレートURL> <タグ/ブランチ>
```

更新対象: `.claude/` 配下（エージェント・コマンド・共通ルール）+ `upgrade.sh`  
更新対象外: `CLAUDE.md`（ルート）・`docs/`・`force-app/`（プロジェクト固有のため触らない）

---

## CLAUDE.md の構成

### `.claude/CLAUDE.md`（共通ルール・触らない）
- エージェント選択基準
- 出力フォーマット
- 禁止操作（本番デプロイ・git push等）
- Salesforceコード品質基準（ガバナ制限・バルク処理・FLS等）

### `CLAUDE.md`（プロジェクト固有・プロジェクトごとに編集）
- Salesforce組織情報（org alias）
- 命名規則（プレフィックス等）
- 主要カスタムオブジェクト
- 過去の判断・決定事項
- 注意事項・地雷
