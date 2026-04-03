# オンボーディングガイド — Salesforce Development OS

Claude Codeを使ったSalesforce開発環境のセットアップ手順書。
新規メンバーはこのドキュメントに沿って環境構築を行う。

---

## 目次

1. [前提条件](#1-前提条件)
2. [Claude Codeのインストール](#2-claude-codeのインストール)
3. [アカウント・認証の設定](#3-アカウント認証の設定)
4. [プロジェクトへの参加](#4-プロジェクトへの参加)
5. [動作確認](#5-動作確認)
6. [初回セットアップ後にやること](#6-初回セットアップ後にやること)
7. [トラブルシューティング](#7-トラブルシューティング)

---

## 1. 前提条件

### 必須ソフトウェア

| ソフトウェア | バージョン | 確認コマンド | インストール |
|---|---|---|---|
| **Node.js** | 18以上 | `node -v` | https://nodejs.org/ |
| **npm** | 9以上 | `npm -v` | Node.jsに同梱 |
| **Git** | 2.30以上 | `git -v` | https://git-scm.com/ |
| **Salesforce CLI (sf)** | 最新 | `sf --version` | https://developer.salesforce.com/tools/salesforcecli |
| **VSCode** | 最新 | — | https://code.visualstudio.com/ |

### 必須アカウント

| アカウント | 用途 | 取得方法 |
|---|---|---|
| **Anthropic（Claude）** | Claude Code利用 | PM/管理者から案内される or https://console.anthropic.com/ |
| **GitHub** | テンプレートリポジトリ・ソースコード管理 | PM/管理者から招待 |
| **Salesforce** | 開発org / Sandbox | PM/管理者から発行 |

---

## 2. Claude Codeのインストール

### 2-1. Claude Code CLI のインストール

```bash
npm install -g @anthropic-ai/claude-code
```

インストール確認:
```bash
claude --version
```

> **補足**: 社内プロキシ環境の場合、npm のプロキシ設定が必要な場合がある。
> ```bash
> npm config set proxy http://proxy.example.com:8080
> npm config set https-proxy http://proxy.example.com:8080
> ```

### 2-2. VSCode拡張機能のインストール

1. VSCodeを開く
2. 拡張機能（`Ctrl+Shift+X`）で「Claude Code」を検索
3. **Claude Code** (Anthropic公式) をインストール

> CLI版とVSCode拡張版のどちらでもテンプレートは動作する。
> チームではVSCode拡張版を推奨（エディタとの統合が便利なため）。

### 2-3. Claude Codeの初回認証

```bash
claude
```

初回起動時にAnthropicアカウントへのログインが求められる。ブラウザが開くのでログインする。

**認証方式の選択肢:**

| 方式 | 対象 |
|---|---|
| Anthropic アカウント（Max/Pro） | 個人プランの場合 |
| API Key | 組織で発行されたキーを使う場合 |

PM/管理者からの指示に従って認証方式を選択する。

---

## 3. アカウント・認証の設定

### 3-1. Gitの初期設定

```bash
git config --global user.name "自分の名前"
git config --global user.email "自分のメールアドレス"
```

### 3-2. GitHubへのSSH鍵設定（未設定の場合）

```bash
ssh-keygen -t ed25519 -C "自分のメールアドレス"
```

公開鍵をGitHubに登録:
1. `cat ~/.ssh/id_ed25519.pub` の内容をコピー
2. GitHub → Settings → SSH and GPG keys → New SSH key

接続テスト:
```bash
ssh -T git@github.com
```

### 3-3. Salesforce CLIの認証

プロジェクト参加後に行う（Step 4 で案内される）。

---

## 4. プロジェクトへの参加

### パターンA: 既存プロジェクトにjoinする場合（ほとんどのケース）

PM/管理者からリポジトリURLが共有される。

```bash
# 1. リポジトリをクローン
git clone <リポジトリURL>
cd <プロジェクトフォルダ>

# 2. Salesforce組織に認証
sf org login web -a dev -r https://test.salesforce.com   # Sandbox
# or
sf org login web -a prod                                   # 本番

# 3. デフォルト組織を設定
sf config set target-org dev

# 4. VSCodeでプロジェクトフォルダを開く
code .
```

> **重要**: VSCodeで開くフォルダは必ず **プロジェクトルート**（`CLAUDE.md` がある階層）。
> サブフォルダを開くとClaude Codeがルールを読み込めない。

### パターンB: 新規プロジェクトを作成する場合（PM/管理者向け）

Claude Codeのセットアップコマンドを使う:

```
/setup-sf-project
```

対話形式でプロジェクト名・作成先・テンプレートURL・組織情報を入力する。
詳細は [運用手順書](operations.md) の「新規プロジェクト作成」を参照。

### 4-1. MCP連携の設定（任意）

プロジェクトで外部ツール連携（GitHub / Slack / Notion等）を使う場合:

```
/setup-mcp
```

対話形式で使用するMCPを選択し、トークンを入力するだけで `.mcp.json` が生成される。

> **セキュリティ**: `.mcp.json`（トークン入り）は `.gitignore` 対象のため、GitHubにpushされない。Git管理されるのは `.mcp.json.example`（トークンなしのテンプレート）のみ。

---

## 5. 動作確認

### 5-1. Claude Codeの起動確認

VSCodeでプロジェクトフォルダを開いた状態で:
1. Claude Code拡張のパネルを開く（サイドバー or `Ctrl+Shift+P` → "Claude Code"）
2. 以下のメッセージを送って応答を確認:

```
このプロジェクトの概要を教えて
```

正常であれば、`CLAUDE.md` の内容を読み取ったプロジェクト固有の回答が返る。

### 5-2. Salesforce接続の確認

```bash
sf org display
```

組織情報（Username, OrgId, Instance URL等）が表示されればOK。

### 5-3. エージェント・コマンドの確認

Claude Codeで以下を試す:

```
/sf-review force-app/main/default/classes/
```

レビューエージェントが起動してレビュー結果が返ればOK。
（まだコードがない場合は「レビュー対象が見つかりません」のようなメッセージが返る）

---

## 6. 初回セットアップ後にやること

### 必須

- [ ] プロジェクトの `CLAUDE.md` を一読する（プロジェクト固有のルール・命名規則を把握）
- [ ] `.claude/CLAUDE.md` を一読する（共通ルール・品質基準を把握）
- [ ] `docs/` 配下の既存ドキュメントを確認する（要件定義・設計書・議事録等）

### 推奨

- [ ] エージェント一覧（10体）とスラッシュコマンド（8個）の役割を把握する → [テンプレート説明書](template-guide.md) 参照
- [ ] 簡単な実装タスクをClaude Codeで1つ試す（例: `/sf-implement テスト用のApexクラスを作成`）
- [ ] `settings.json` の権限設定（自動許可・自動拒否）を確認する

---

## 7. トラブルシューティング

### Claude Codeが起動しない

| 症状 | 原因 | 対処 |
|---|---|---|
| `claude: command not found` | CLIが未インストール | `npm install -g @anthropic-ai/claude-code` |
| 認証エラー | Anthropicアカウント未認証 | `claude` を実行して再認証 |
| API Keyエラー | キーが無効/期限切れ | PM/管理者に確認 |

### CLAUDE.mdが読み込まれない

| 症状 | 原因 | 対処 |
|---|---|---|
| プロジェクトルールが無視される | VSCodeで開いたフォルダがルートでない | `CLAUDE.md` がある階層でVSCodeを開き直す |
| エージェントが起動しない | `.claude/` フォルダが欠損 | テンプレートから再コピー |

### Salesforce CLI関連

| 症状 | 原因 | 対処 |
|---|---|---|
| `sf: command not found` | 未インストール | https://developer.salesforce.com/tools/salesforcecli |
| 認証期限切れ | セッション切れ | `sf org login web -a <alias>` で再認証 |
| デプロイ失敗 | メタデータ競合 | `sf project retrieve start` で最新を取得してから再試行 |

### ネットワーク・プロキシ

社内ネットワークでnpm/git/sf CLIがブロックされる場合:
```bash
# npm
npm config set proxy http://proxy:port
npm config set https-proxy http://proxy:port

# git
git config --global http.proxy http://proxy:port

# sf CLI — 環境変数で設定
export HTTP_PROXY=http://proxy:port
export HTTPS_PROXY=http://proxy:port
```

---

## 次のステップ

- [テンプレート説明書](template-guide.md) — エージェント・コマンド・設定ファイルの詳細リファレンス
- [管理者向けセットアップガイド](project-setup-guide.md) — PM向け。新規案件/保守案件のセットアップ手順
- [運用手順書](operations.md) — プロジェクト運用フロー・テンプレート管理・アップグレード手順
