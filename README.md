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

**推奨実行順序（初期セットアップ）**

| 順序 | コマンド | 備考 |
|---|---|---|
| 1 | `/sf-setup` | 本番組織の認証（記憶形成は本番推奨） |
| 2 | `/sf-retrieve` | メタデータをローカルに取得 |
| 3 | `/sf-memory`（全カテゴリ） | 会話形式でカテゴリ選択。更新時はカテゴリを個別指定 |

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

#### オブジェクト定義書 詳細フロー

| ステップ | 内容 | 備考 |
|---|---|---|
| ① 接続先確認 | 認証中の組織を自動表示 | `.sf/config.json` の target-org を参照 |
| ② 作成者名 | 改版履歴・表紙に記録 | 初回作成者を固定。更新者は別行 |
| ③ 出力フォルダ | フォルダパスを入力 | 既存ファイルがあれば更新、なければ新規 v1.0 |
| ④ バージョン種別 | マイナー: 変更項目を赤字表示 / メジャー: 赤字をリセット | 更新時のみ選択 |
| ⑤ 対象オブジェクト | API 名またはラベル名で入力（複数可・区切り文字自由） | 自動で API 名に解決 |
| ⑥ 生成確認 | 設定を確認してから生成開始 | |

#### `/sf-design` — 2層設計書の概要

設計書を「読者が誰か」で2層に分けて生成するコマンド。1つの資料に全部書くと実装者には抽象的すぎる問題を解消する。

| 層 | 対象読者 | 内容 | 出力先 |
|---|---|---|---|
| **詳細設計** | エンジニア | 機能グループ単位のコンポーネント仕様・インターフェース・画面項目 | `{output_dir}/02_詳細設計/` |
| **プログラム設計** | 実装者 | コンポーネント単位の SOQL・DML・処理フロー詳細 | `{output_dir}/03_プログラム設計/` |

加えて、**機能一覧.xlsx** のみの再生成にも対応（3種別マルチセレクト）。詳細設計は `docs/.sf/feature_groups.yml`（業務グループ定義）が必要で、`/sf-memory` カテゴリ4 で生成される。

---

## settings.json（自動ブロック設定）

| 操作 | 挙動 |
|---|---|
| 本番 org（`*prod*` / `*production*`）へのデプロイ | 自動拒否 |
| `rm -rf` / `.claude` の削除 | 自動拒否 |
| `.claude/` / `scripts/` 配下の編集・書き込み | 自動拒否（テンプレート保護） |
| Sandbox 等へのデプロイ | 自動実行 |

チーム運用・PR 運用に切り替えるときは、`settings.json` の `__pending.git_workflow.rules` を `permissions.deny` に移動して `main` / `develop` への直接 push を禁止する。

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

## テンプレートの更新

プロジェクト作成後にテンプレート側で更新があった場合、取り込める:

```bash
bash scripts/upgrade.sh
```

`.claude/` / `scripts/` / `.gitignore` のみ更新され、プロジェクト固有ファイル（`CLAUDE.md` / `docs/` / `.mcp.json` / `force-app/`）は保護される。
