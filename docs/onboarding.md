# オンボーディングガイド — Salesforce + Claude Code

新規メンバーが自分で環境を構築し、開発を始めるまでの手順書。

---

## 全体の流れ

```
1. 必要なソフトウェアをインストール（10分）
2. プロジェクトを取得する（5分）
   - 新規プロジェクト → コマンド1行でセットアップ
   - 既存プロジェクト → git clone + SF組織認証
3. 動作確認（5分）
4. プロジェクトのルールを読む（10分）
```

---

## 1. 必要なソフトウェアのインストール

### 全員必須

| ソフトウェア | 確認コマンド | インストール先 |
|---|---|---|
| **Node.js** 18以上 | `node -v` | https://nodejs.org/ |
| **Git** 2.30以上 | `git -v` | https://git-scm.com/ |
| **Salesforce CLI (sf)** | `sf --version` | https://developer.salesforce.com/tools/salesforcecli |
| **VSCode** | — | https://code.visualstudio.com/ |

### Claude Codeのインストール

```bash
# CLI のインストール
npm install -g @anthropic-ai/claude-code

# 確認
claude --version
```

VSCode拡張機能:
1. `Ctrl+Shift+X` で拡張機能を開く
2. 「Claude Code」で検索
3. **Anthropic公式** のものをインストール

### Claude Codeの初回認証

```bash
claude
```

ブラウザが開くのでAnthropicアカウントでログインする。
認証方式（個人アカウント / 組織API Key）は管理者の指示に従う。

---

## 2. プロジェクトを取得する

**テンプレートを事前にダウンロードする必要はない。** コマンド1行でSFDXプロジェクト作成からファイル配置まで全て自動で行われる。

> **注意**: このコマンドは **Git Bash** で実行する。コマンドプロンプト（cmd.exe）やPowerShellでは動作しない。
> Git Bashの起動方法: スタートメニューで「Git Bash」を検索 または 対象フォルダを右クリック →「Git Bash Here」

### コマンド

```bash
# 新規プロジェクト（テンプレートから作成）
curl -sSL https://raw.githubusercontent.com/h-omata825/sf-claude-template/main/scripts/setup.sh | bash -s <フォルダ名> <作成先パス>

# 既存プロジェクトに参加（プロジェクトリポジトリをソースに指定）
curl -sSL https://raw.githubusercontent.com/h-omata825/sf-claude-template/main/scripts/setup.sh | bash -s <フォルダ名> <作成先パス> <プロジェクトリポジトリURL>
```

| 引数 | 必須 | 説明 |
|---|---|---|
| `<フォルダ名>` | ✓ | 作成されるフォルダの名前。`<作成先パス>/<フォルダ名>/` が生成される |
| `<作成先パス>` | ✓ | フォルダを作る場所。パスにスペースや日本語が含まれる場合はダブルクォートで囲む |
| `<プロジェクトリポジトリURL>` | — | 既存プロジェクトに参加する場合のみ指定 |

どちらも挙動は同じ。ソースになるリポジトリが「テンプレート」か「既存プロジェクト」かの違いだけ。

### 実行例

```bash
# 新規プロジェクト
curl -sSL https://raw.githubusercontent.com/h-omata825/sf-claude-template/main/scripts/setup.sh | bash -s my-sf-project /c/workspace

# 既存プロジェクト参加
curl -sSL https://raw.githubusercontent.com/h-omata825/sf-claude-template/main/scripts/setup.sh | bash -s project-a /c/workspace https://github.com/your-org/project-a.git
```

```
[INFO]  SFDXプロジェクトを作成中...
[OK]    SFDXプロジェクト作成完了: /c/workspace/project-a
[INFO]  テンプレートを取得中...
[INFO]  テンプレートを配置中...

==========================================
  セットアップ完了
==========================================

  次のステップ:
    1. cd /c/workspace/project-a
    2. Claude Code を起動
    3. /setup-sf-project を実行（組織認証・メタデータ取得）
    4. CLAUDE.md を編集してプロジェクト固有情報を記入
    5. /setup-mcp を実行してGitHub連携を設定
```

### 次のステップ: SF組織に接続する

プロジェクトフォルダをVSCodeで開いてClaude Codeパネルから:

```
/setup-sf-project
```

対話形式でSalesforce組織への認証とメタデータ取得が行われる。

```
接続するSalesforce組織の種別を入力してください:
  prod  — 本番/Developer Edition
  dev   — Sandbox
  skip  — 後で設定する

種別: dev
```

ブラウザが開くのでSalesforceにログインする。

> **重要**: VSCodeで開くフォルダは必ず **プロジェクトルート**（`CLAUDE.md` がある階層）。
> サブフォルダを開くとClaude Codeがルールを読み込めない。

### MCP連携の設定（必要な場合のみ）

GitHub・Slack・Notion等の外部ツール連携を使う場合のみ。Claude Codeパネルから:

```
/setup-mcp
```

対話形式で接続先を選択し、トークンを入力する。
`.mcp.json` が生成される（`.gitignore` 対象なのでGitHubにpushされない）。

---

## 3. 動作確認

### Claude Codeの起動確認

VSCodeのClaude Codeパネルで以下を送信:

```
このプロジェクトの概要を教えて
```

`CLAUDE.md` の内容に基づいたプロジェクト固有の回答が返ればOK。

「一般的なSalesforceの説明」しか返ってこない場合、VSCodeで開いているフォルダが間違っている。

### Salesforce接続の確認

```bash
sf org display
```

Username・OrgId・Instance URL等が表示されればOK。

### コマンドの確認

```
/sf-analyze
```

組織に接続して情報収集が始まればOK（初回は中断しても問題ない）。

---

## 4. プロジェクトのルールを読む

### 必須（作業前に必ず読む）

| ファイル | 内容 | 所要時間 |
|---|---|---|
| `CLAUDE.md`（ルート） | プロジェクト固有のルール・命名規則・組織情報・決定事項 | 5分 |
| `docs/` 配下のドキュメント | 要件定義書・設計書・オブジェクト定義書 | 5分 |

### 推奨

| やること | 説明 |
|---|---|
| [テンプレート説明書](template-guide.md) を読む | エージェント10体・コマンド8個の役割を把握 |
| 簡単な作業をClaude Codeで1つ試す | 例: 「Accountオブジェクトの項目一覧を教えて」 |

### 触らないファイル

| ファイル | 理由 |
|---|---|
| `.claude/CLAUDE.md` | 共通ルール。テンプレート管理者が管理 |
| `.claude/agents/` | エージェント定義。`/upgrade` で更新される |
| `.claude/commands/` | コマンド定義。`/upgrade` で更新される |
| `.claude/settings.json` | 権限設定。Git管理対象でチーム全員に強制 |

これらは `settings.json` で編集がブロックされているため、Claude Codeからも変更できない。

---

## 5. テンプレートの更新

テンプレートが更新された場合（管理者から案内がある）、プロジェクトルートで:

```bash
bash scripts/upgrade.sh
```

自動で以下が行われる:
1. テンプレートリポジトリから最新版を取得
2. 変更があるファイルの一覧・差分を表示
3. 確認後、`.claude/` 配下を更新

```
==========================================
  テンプレートに以下の変更があります
==========================================

  追加: .claude/agents/new-agent.md（新規エージェント）
  更新: .claude/CLAUDE.md（共通ルール）
  更新: .claude/commands/sf-analyze.md

  合計: 3件の変更

適用しますか？ (y/N): y
```

**更新されるもの**: `.claude/CLAUDE.md` / エージェント / コマンド / スクリプト
**更新されないもの**: `CLAUDE.md`（ルート）/ `docs/` / `force-app/` / `.mcp.json`

> 特定のバージョンを指定する場合: `bash scripts/upgrade.sh v1.2.0`

---

## トラブルシューティング

### setup.sh

| 症状 | 対処 |
|---|---|
| `error: Git がインストールされていません` | Git をインストール |
| `error: Salesforce CLI がインストールされていません` | sf CLI をインストール |
| `error: <パス> は既に存在します` | 同名フォルダがある。別名にするか既存フォルダを移動 |
| テンプレート取得失敗 | ネットワーク接続確認。プロキシ環境なら Git のプロキシ設定が必要 |

### Claude Code

| 症状 | 対処 |
|---|---|
| `claude: command not found` | `npm install -g @anthropic-ai/claude-code` |
| 認証エラー | `claude` を再実行して認証し直す |
| API Keyエラー | 管理者にキーの有効性を確認 |
| プロジェクトルールが反映されない | `CLAUDE.md` がある階層でVSCodeを開き直す |
| エージェントが起動しない | `.claude/` フォルダの存在を確認。なければ `bash scripts/upgrade.sh` で復旧 |

### Salesforce CLI

| 症状 | 対処 |
|---|---|
| `sf: command not found` | https://developer.salesforce.com/tools/salesforcecli からインストール |
| 認証期限切れ | `sf org login web -a <alias>` で再認証 |
| Git Bashで `sf` が動かない | フルパスで実行: `"C:/Program Files/sf/client/bin/node.exe" "C:/Program Files/sf/client/bin/run.js" <サブコマンド>` |

### ネットワーク・プロキシ

社内プロキシ環境の場合:

```bash
# npm
npm config set proxy http://proxy:port
npm config set https-proxy http://proxy:port

# Git
git config --global http.proxy http://proxy:port

# Salesforce CLI（環境変数）
export HTTP_PROXY=http://proxy:port
export HTTPS_PROXY=http://proxy:port
```

---

## 関連資料

- [テンプレート説明書](template-guide.md) — エージェント・コマンド・設定の詳細リファレンス
- [運用手順書](operations.md) — 日常の開発フロー
