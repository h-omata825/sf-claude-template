# Salesforce Development OS

Salesforce開発プロジェクトで使うClaude Code設定のテンプレート。
このフォルダをプロジェクト用にコピーして使う。

---

## テンプレートの使い方

1. このテンプレートフォルダをコピーしてプロジェクト名にリネームする
2. プロジェクトフォルダ内でSFDXプロジェクトを生成する
```bash
cd my-project
sf project generate --name . --manifest
```
3. ルートの `CLAUDE.md` をプロジェクト固有の情報に書き換える
4. VSCodeでプロジェクトフォルダを開く（サブフォルダではなくルートを開くこと）
5. SF CLIで組織に認証する
```bash
sf org login web --alias project-dev --instance-url https://test.salesforce.com
sf org login web --alias project-prod
```

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
    agents/              ← AIエージェント定義（10体）
    commands/            ← スラッシュコマンド定義（6個）
    settings.json        ← 権限・MCP設定
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

## スラッシュコマンド（6個）

| コマンド | 内容 | エージェント |
|---|---|---|
| `/sf-implement [内容]` | 機能実装 | salesforce-dev |
| `/sf-deploy [対象]` | デプロイ前チェック・デプロイ支援 | salesforce-dev |
| `/sf-review [対象]` | コード・メタデータのレビュー | reviewer |
| `/sf-debug [症状]` | バグ調査・障害対応 | maintenance |
| `/feedback [内容]` | 決定事項・気づきをCLAUDE.mdに記録 | assistant |
| `/save-doc` | 添付資料をMarkdownに変換してdocsに保存 | doc-writer |

> その他のエージェント（qa-engineer, salesforce-architect, project-manager, data-manager, integration-dev）は自然言語で直接呼び出せる。

---

## 権限設定（settings.json）

### 自動許可
- すべてのBashコマンドを自動許可（`Bash(*)`）

### 自動拒否（確認なしに実行しない）
- 本番環境へのデプロイ（`*prod*` / `*production*`）
- `git push` / `git commit`
- `git reset --hard`

### MCPサーバー（デフォルトは無効）
有効化する場合は `settings.json` の対象サーバーから `"disabled": true` を削除する。

| MCP | 用途 |
|---|---|
| `git` | ローカルgitリポジトリ操作 |
| `filesystem` | ローカルファイルアクセス拡張 |
| `gdrive` | Google Driveアクセス |
| `notion` | Notionページの読み書き（要トークン設定） |

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
