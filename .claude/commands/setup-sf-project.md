---
description: "Salesforce組織の認証・package.xml生成・メタデータ取得を実行する。setup.sh でプロジェクト作成後に実行する。"
---

`setup.sh` でプロジェクトフォルダの作成が完了している前提で、Salesforce組織への接続とメタデータ取得を行う。

## 事前チェック

以下を確認する:

```bash
sf --version
test -f sfdx-project.json && echo "OK" || echo "NOT FOUND"
```

- `sf` が見つからない場合 → Salesforce CLI のインストールを案内して中断
- `sfdx-project.json` が見つからない場合 → 「SFDXプロジェクトのルートで実行してください」と案内して中断

---

## Step 1: 組織の種別を確認

ユーザーに以下を質問する:

```
接続するSalesforce組織の種別を入力してください
  prod   — 本番 / Developer Edition（login.salesforce.com）
  dev    — Sandbox（test.salesforce.com）
  skip   — 後で設定する
  その他 — カスタムエイリアス（本番 or Sandboxかも聞く）
```

---

## Step 2: 組織認証

`scripts/setup-sf-project.sh` を実行する:

```bash
bash scripts/setup-sf-project.sh <エイリアス> [sandbox]
```

引数:
- `prod` の場合: `bash scripts/setup-sf-project.sh prod`
- `dev` の場合: `bash scripts/setup-sf-project.sh dev`
- カスタムエイリアス + Sandbox: `bash scripts/setup-sf-project.sh <alias> sandbox`
- カスタムエイリアス + 本番: `bash scripts/setup-sf-project.sh <alias>`
- `skip` の場合: このステップをスキップ

スクリプト内でブラウザが開くのでログインを促す。認証完了後、package.xml生成とメタデータ取得まで自動で行われる。

---

## Step 3: 完了報告

```
============================================
  組織セットアップ完了
============================================

  組織: <エイリアス>（認証済み）
  メタデータ: force-app/ に保存済み

  次のステップ:
    1. CLAUDE.md を開いてプロジェクト固有情報を記入
    2. /setup-mcp でMCP連携を設定（Backlog・GitHub等）
    3. /sf-analyze で組織を解析して資料を自動生成
```
