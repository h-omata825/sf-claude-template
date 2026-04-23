# sf-claude-template

Salesforce 開発プロジェクト向けの Claude Code テンプレート。
`scripts/setup.sh` で新規プロジェクトを生成すると、本テンプレートの `.claude/` / `CLAUDE.md` / `docs/` / `scripts/` 一式がプロジェクトに展開される。

---

## 前提条件

| ツール | 最低バージョン |
|---|---|
| Git | 2.30+ |
| Salesforce CLI (`sf`) | 2.0+ |
| Node.js | 18+ |
| Python | 3.10+ |
| Claude Code | 最新版 |

---

## ディレクトリ構成

| パス | 役割 |
|---|---|
| `.claude/agents/` | 専門エージェント定義 |
| `.claude/commands/` | スラッシュコマンド定義 |
| `.claude/settings.json` | 権限・フック設定 |
| `CLAUDE.md` | プロジェクト固有ルール（担当者名・組織 alias 等） |
| `docs/` | 設計書・要件・議事録 |
| `scripts/` | セットアップ・アップグレード・Python 補助スクリプト |

---

## スラッシュコマンド（9個）

### セットアップ系

| コマンド | 概要 | 補足 |
|---|---|---|
| `/sf-setup` | SF 組織への認証（prod / dev / skip の対話形式） | 初回のみ |
| `/setup-mcp` | GitHub・Slack・Notion 等の MCP 連携を設定 | 初回のみ |
| `/upgrade [タグ]` | 大本テンプレートから `.claude/` 配下を更新 | タグ省略で main ブランチ |
| `/git-sync` | テンプレート更新・プロジェクトの pull/push を対話形式で実行 | |

### 組織記憶系

| コマンド | 概要 | 補足 |
|---|---|---|
| `/sf-retrieve [対象]` | package.xml を生成してメタデータをローカルに取得 | |
| `/sf-memory` | 会話形式でカテゴリを選択し、組織の記憶形成を実行 | 4カテゴリ：組織概要・オブジェクト・マスタデータ・設計/機能グループ |

### 保守・開発系

| コマンド | 概要 | 補足 |
|---|---|---|
| `/backlog [課題ID]` | Backlog 課題の分析 → 対応方針提案 → 実装 → テスト → デプロイまで一気通貫 | ユーザー承認後に実装へ |

### ドキュメント生成系

| コマンド | 概要 | 補足 |
|---|---|---|
| `/sf-doc` | 基本設計資料（プロジェクト概要書・オブジェクト定義書）を対話形式で生成 | 上流 → 下流の順に分岐 |
| `/sf-design` | 2層設計書（詳細設計・プログラム設計）＋機能一覧を対話形式で生成 | 読者・目的に合わせて層を選択 |

#### `/sf-doc` 資料種別

| 資料 | 出力 | ソース |
|---|---|---|
| プロジェクト概要書 | Excel | `docs/overview/` `docs/requirements/` `docs/architecture/` `docs/catalog/` `docs/flow/` |
| オブジェクト定義書 | Excel | Salesforce 組織メタデータに直接接続 |

---

## 新規プロジェクト作成

```bash
curl -sSL https://raw.githubusercontent.com/h-omata825/sf-claude-template/main/scripts/setup.sh | bash -s プロジェクト名
```

作成後、Python ライブラリをインストール（設計書生成機能を使う場合）:

```bash
pip install -r scripts/python/sf-doc-mcp/requirements.txt
```

---

## テンプレートの更新（/upgrade）

プロジェクト作成後にテンプレート側で更新があった場合、取り込める:

```bash
bash scripts/upgrade.sh
```

`.claude/` / `scripts/` / `.gitignore` のみ更新され、プロジェクト固有ファイル（`CLAUDE.md` / `docs/` / `.mcp.json` / `force-app/`）は保護される。

---

## Git 同期（/git-sync）

テンプレート更新・プロジェクトの pull/push を対話形式で実行する。3種類の操作から選択:

| 操作 | 内容 |
|---|---|
| テンプレート部分を更新 | `upgrade.sh` を実行し、変更があれば自動で `git push` |
| プロジェクト部分を取得 | `git pull` で最新を取得 |
| プロジェクト部分を保存 | 変更ファイル（`docs/` / `CLAUDE.md`）を選択して自動コミット + `git push` |

`/upgrade` はテンプレート更新のみ。`/git-sync` はテンプレート更新とプロジェクト側 pull/push の両方を1コマンドで実行できる。
