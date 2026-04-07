# Salesforce Development OS

Salesforce開発プロジェクトで使うClaude Code設定のテンプレート。
このフォルダをプロジェクト用にコピーして使う。

---

## クイックスタート

### 方法1: ワンコマンドセットアップ（推奨）

テンプレートを持っていなくても、以下の1行で新規プロジェクトを作成できる:

```bash
curl -sSL https://raw.githubusercontent.com/h-omata825/sf-claude-template/develop/scripts/setup.sh | bash -s <プロジェクト名>
```

作成先を指定する場合:

```bash
curl -sSL https://raw.githubusercontent.com/h-omata825/sf-claude-template/develop/scripts/setup.sh | bash -s <プロジェクト名> <作成先パス>
```

実行後:
1. `cd <プロジェクト名>` でプロジェクトフォルダに移動
2. Claude Code を起動
3. `/setup-sf-project` を実行 → 組織認証・メタデータ取得を対話形式で実行
4. `CLAUDE.md` を編集してプロジェクト固有情報を記入
5. `/setup-mcp` を実行 → GitHub等のMCP連携を設定

### 方法2: リポジトリ clone 後にセットアップ

```bash
git clone https://github.com/h-omata825/sf-claude-template.git
cd sf-claude-template
bash scripts/setup.sh <プロジェクト名> <作成先パス>
```

### 方法3: 手動セットアップ

1. `sf project generate --name <プロジェクト名> --manifest` でSFDXプロジェクトを作成
2. テンプレートの `.claude/`, `CLAUDE.md`, `docs/`, `scripts/` をコピー
3. `.gitignore` に `.mcp.json` を追加
4. `CLAUDE.md` をプロジェクト固有の情報に書き換える
5. `/setup-sf-project` で組織認証
6. `/setup-mcp` でMCP連携を設定

### 前提条件

- [Salesforce CLI](https://developer.salesforce.com/tools/salesforcecli) がインストール済み
- [Git](https://git-scm.com/) がインストール済み
- [Claude Code](https://claude.ai/code) がインストール済み

---

## フォルダ構成

```
project/                    ← sf project generate で生成されたSFDXプロジェクト
  sfdx-project.json         （SFDXが生成）
  force-app/main/default/   （SFDXが生成）
  manifest/                 （SFDXが生成）
  CLAUDE.md              ← プロジェクト固有ルール（コピー後に編集する）
  .gitignore             ← テンプレートからコピー
  .claude/               ← テンプレートからコピー（中身は触らない）
    CLAUDE.md            ← Salesforce共通ルール
    VERSION              ← テンプレートバージョン（upgrade.sh が参照）
    agents/              ← AIエージェント定義
    commands/            ← スラッシュコマンド定義
    settings.json        ← 権限設定（Git管理対象・チーム共有）
  scripts/               ← シェルスクリプト（定型処理の自動化）
    setup.sh             ← 新規プロジェクト作成（curl で直接実行可能）
    setup-sf-project.sh  ← SF組織認証・メタデータ取得
    setup-mcp.sh         ← MCP連携（.mcp.json）の設定
    upgrade.sh           ← テンプレート更新（差分検出→適用）
    sf-package.sh        ← package.xml 生成・メタデータ取得
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
| `reviewer` | コードレビュー、セキュリティ監査、PRレビュー支援 |
| `qa-engineer` | テスト計画、テストケース作成、UAT支援 |
| `salesforce-architect` | 要件定義、設計書作成・設計レビュー、オブジェクト定義書、影響調査 |
| `project-manager` | タスク管理、スプリント計画、議事録、進捗報告 |
| `doc-writer` | 手順書、マニュアル、リリースノート、資料作成 |
| `data-manager` | データ移行、SOQL最適化、Data Loader、クレンジング |
| `integration-dev` | 外部API連携、REST/SOAP、Platform Events、Named Credentials |
| `assistant` | 調査、メール下書き、翻訳、その他アドホック作業 |

---

## スラッシュコマンド（13個）

| コマンド | 内容 | エージェント |
|---|---|---|
| `/sf-implement [内容]` | 機能実装 | salesforce-dev |
| `/sf-deploy [対象]` | デプロイ前チェック・デプロイ支援 | salesforce-dev |
| `/sf-review [対象]` | コード・メタデータのレビュー | reviewer |
| `/sf-debug [症状]` | バグ調査・障害対応 | maintenance |
| `/sf-analyze [資料]` | 組織解析→プロフィール・要件定義書を自動生成 | salesforce-architect |
| `/sf-design [内容]` | 機能別設計書の作成・既存設計書のインポート | salesforce-architect |
| `/sf-catalog` | オブジェクト・項目定義書の自動生成 | salesforce-architect |
| `/sf-data [内容]` | データ移行・SOQL最適化・クレンジング | data-manager |
| `/feedback [内容]` | 決定事項・気づきをCLAUDE.mdに記録 | assistant |
| `/save-doc` | 添付資料をMarkdownに変換してdocsに保存 | doc-writer |
| `/setup-mcp` | MCP連携の設定（新規作成・更新・削除に対応） | assistant |
| `/setup-sf-project` | 対話形式でSFDXプロジェクトを新規作成 | salesforce-dev |
| `/upgrade` | テンプレートの最新版を取得して.claude/配下を更新 | assistant |

---

## 権限設定（settings.json）

`settings.json` は **Git管理対象**。チーム全員に同じ権限制限が強制される。

### 自動許可
- すべてのBashコマンドを自動許可（`Bash(*)`）

### 自動拒否（Claude Codeが実行前にブロック）
- 本番環境へのデプロイ（`*prod*` / `*production*`）
- `rm -rf` / `.claude` の削除
- `.claude/` 配下の編集・書き込み（テンプレート保護）

> Git操作（push/commit/reset等）の制限は運用開始時に `settings.json` の deny に追加する想定。

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

テンプレートに更新があった場合、プロジェクトフォルダで `/upgrade` またはスクリプトを直接実行:

```bash
# Claude Code 経由
/upgrade

# スクリプト直接実行
bash scripts/upgrade.sh                    # develop ブランチの最新版
bash scripts/upgrade.sh v1.2.0             # 指定タグ/ブランチ
bash scripts/upgrade.sh develop <URL>      # 別リポジトリ
```

更新対象: `.claude/` 配下（エージェント・コマンド・共通ルール・settings.json）+ `scripts/`  
更新対象外: `CLAUDE.md`（ルート）・`docs/`・`force-app/`・`.mcp.json`（プロジェクト固有のため触らない）

スクリプトが差分を検出して一覧表示し、確認後に適用する。バージョンは `.claude/VERSION` で管理。

---

## できること・できないこと

### Claude Codeが自由にできること

| 操作 | 例 |
|---|---|
| Salesforceメタデータの作成・編集 | Apex, LWC, Flow, オブジェクト定義 |
| Sandbox環境へのデプロイ | `sf project deploy start --target-org dev` |
| テスト実行 | `sf apex run test` |
| `docs/` 配下の資材追加・編集 | 設計書、要件定義書、議事録 |
| `CLAUDE.md`（ルート）の編集 | プロジェクト固有ルールの追記 |
| Git読み取り操作 | `git pull`, `git fetch`, `git status`, `git diff` |
| ブランチ作成・切替 | `git checkout -b feature/xxx` |
| Git commit / push | 確認ダイアログ経由で実行可能 |
| SOQL/SOSLの実行 | `sf data query` |
| ローカルファイルの読み取り | 参考資料の確認、ログ解析 |

### Claude Codeができないこと（自動拒否・解除不可）

| 操作 | 理由 |
|---|---|
| `.claude/` 配下の編集・書き込み | テンプレート保護（`/upgrade` で更新） |
| 本番環境へのデプロイ | 人間の確認が必須 |
| `rm -rf` / `.claude` の削除 | 破壊的操作の防止 |
| プロジェクトフォルダ外への書き込み | 共有フォルダ・他プロジェクトの保護（ルールで制御） |
| 機密情報の出力 | トークン・パスワード・個人情報 |

### 品質ゲート（自動品質チェック）

コード実装・設計書作成などの成果物は、完了前に**自動でレビューエージェントの基準で品質チェック**を実行する。

| 作業 | チェック担当 |
|---|---|
| Apex / LWC / Flow 実装 | reviewer エージェント |
| テストクラス作成 | qa-engineer エージェント |
| 設計書・要件定義書 | salesforce-architect エージェント（セルフレビュー） |

問題があれば修正案を提示。ユーザーが「スキップ」と言えば省略可能。

---

## CLAUDE.md の構成

### `.claude/CLAUDE.md`（共通ルール・触らない）
- エージェント選択基準
- 出力フォーマット
- セキュリティ・権限ルール
- 品質ゲート（自動レビュー定義）
- 禁止操作（本番デプロイ・git push等）
- Salesforceコード品質基準（ガバナ制限・バルク処理・FLS等）

### `CLAUDE.md`（プロジェクト固有・プロジェクトごとに編集）
- Salesforce組織情報（org alias）
- 命名規則（プレフィックス等）
- 主要カスタムオブジェクト
- 過去の判断・決定事項
- 注意事項・地雷
