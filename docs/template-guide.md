# テンプレート利用ガイド

## 概要

このテンプレートは Salesforce 保守プロジェクトに Claude Code を導入するための設定一式です。

---

## 初回セットアップ手順

### 1. セットアップスクリプトの実行

```bash
bash scripts/setup.sh プロジェクト名
```

以下が自動で行われます:
- SFDX プロジェクトの作成
- `.claude/` テンプレートの配置
- 初期フォルダ構成の作成

### 2. CLAUDE.md の編集

ルートの `CLAUDE.md` を開き、以下を記入します:

- プロジェクト名・システム名
- 担当者情報
- プロジェクト固有の命名規則・品質基準
- 注意事項・地雷情報

### 3. Salesforce 組織の接続

```
/sf-setup
```

ブラウザが開くので Salesforce にログインします。

### 4. メタデータの取得

```
/sf-retrieve
```

`manifest/package.xml` を生成してメタデータを `force-app/` に取得します。

### 5. 外部ツール連携（任意）

```
/setup-mcp
```

Backlog・GitHub・Slack・Notion・Playwright との連携を設定します。

### 6. 組織情報の記録

```
/sf-memory
```

組織のオブジェクト定義・要件・設計情報を `docs/` に自動生成します。
**初回は本番組織で実施することを推奨します。**

---

## 日常的な使い方

### 課題対応

```
/backlog GF-XXX
```

Backlog の課題 ID を指定して対応フローを開始します（調査→方針→実装→テスト→デプロイ）。

### 設計書の生成・更新

```
/sf-doc
```

オブジェクト定義書・機能別設計書・データモデル図などを生成します。

---

## フォルダ構成

```
プロジェクトルート/
├── CLAUDE.md                   # プロジェクト固有設定（要編集）
├── .claude/
│   ├── agents/                 # エージェント定義（編集不要）
│   ├── commands/               # スラッシュコマンド（編集不要）
│   └── settings.json           # 権限設定（編集不要）
├── docs/
│   ├── overview/               # 組織概要・用語集
│   ├── requirements/           # 要件定義書
│   ├── design/                 # 機能別設計書
│   ├── catalog/                # オブジェクト定義書
│   ├── data/                   # マスタデータ
│   ├── architecture/           # システム構成情報
│   ├── changelog.md            # 変更履歴
│   ├── decisions.md            # 判断記録
│   └── effort-log.md           # 工数記録
├── force-app/                  # Salesforce メタデータ
├── manifest/                   # package.xml
└── scripts/                    # セットアップスクリプト
```

---

## テンプレートの更新

テンプレートの新バージョンが公開されたら:

```
/upgrade
```

`CLAUDE.md`（ルート）・`docs/`・`force-app/` は上書きされません。

---

## よくある質問

**Q: sf コマンドが見つからないと言われる**
A: `npm install -g @salesforce/cli` で Salesforce CLI をインストールしてください。

**Q: /sf-memory がエラーになる**
A: `/sf-setup` で組織認証が完了しているか確認してください。

**Q: .claude/ 配下のファイルを編集したい**
A: テンプレートリポジトリ側で編集して `/upgrade` で配布するのが正しい手順です。緊急の場合は `settings.json` の deny ルールを一時的に変更してください。
