# sf-claude-template

Salesforce 開発プロジェクト向けの Claude Code テンプレート。
`scripts/setup.sh` で新規プロジェクトを生成すると、本テンプレートの `.claude/` / `CLAUDE.md` / `docs/` / `scripts/` 一式がプロジェクトに展開される。

## 主なコマンド

| コマンド | 用途 |
|---|---|
| `/sf-setup` | Salesforce 組織の認証 |
| `/sf-retrieve` | メタデータ取得（`force-app/` に展開） |
| `/sf-memory` | 組織情報の収集・ナレッジドキュメント生成 |
| `/sf-doc` | オブジェクト項目定義書の生成 |
| `/sf-design` | 基本設計・ドメイン設計・詳細設計の生成 |
| `/setup-mcp` | Backlog / Notion / GitHub 等の外部連携設定 |

詳細は `.claude/CLAUDE.md` および `.claude/commands/` 配下のコマンド定義を参照。

## ディレクトリ構成

| パス | 役割 |
|---|---|
| `.claude/agents/` | 専門エージェント定義 |
| `.claude/commands/` | スラッシュコマンド定義 |
| `CLAUDE.md` | プロジェクト固有ルール（担当者名・組織 alias 等） |
| `docs/` | 設計書・要件・議事録 |
| `scripts/` | セットアップ・アップグレード・Python 補助スクリプト |

## 前提条件

| ツール | 最低バージョン |
|---|---|
| Git | 2.30+ |
| Salesforce CLI (`sf`) | 2.0+ |
| Node.js | 18+ |
| Python | 3.10+ |
| Claude Code | 最新版 |

## 新規プロジェクト作成

```bash
curl -sSL https://raw.githubusercontent.com/h-omata825/sf-claude-template/main/scripts/setup.sh | bash -s プロジェクト名
```

作成後、Python ライブラリをインストール（設計書生成機能を使う場合）:

```bash
pip install -r scripts/python/sf-doc-mcp/requirements.txt
```

## テンプレートの更新

プロジェクト作成後にテンプレート側で更新があった場合、取り込める:

```bash
bash scripts/upgrade.sh
```

`.claude/` / `scripts/` / `.gitignore` のみ更新され、プロジェクト固有ファイル（`CLAUDE.md` / `docs/` / `.mcp.json` / `force-app/`）は保護される。
