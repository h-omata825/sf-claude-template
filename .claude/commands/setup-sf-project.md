---
description: "Salesforce組織の認証を行う。setup.sh でプロジェクト作成後に実行する。"
---

## 事前チェック

```bash
sf --version && test -f sfdx-project.json && echo "OK"
```

失敗した場合: sfが無ければCLIインストールを案内、sfdx-project.jsonが無ければ「プロジェクトルートで実行してください」と伝えて終了。

## Step 1: 組織種別の選択

AskUserQuestion ツールを使い、以下のオプションをクリック選択式で提示する:

- `prod` — 本番 / Developer Edition
- `dev` — Sandbox
- `custom` — カスタムエイリアス（選択後に名前を入力してもらう）
- `skip` — 後で設定する

## Step 2: 認証

選択に応じて実行:

```bash
bash scripts/setup-sf-project.sh prod        # 1の場合
bash scripts/setup-sf-project.sh dev         # 2の場合
bash scripts/setup-sf-project.sh <alias>     # 3の場合（sandboxなら第2引数にsandbox）
```

スクリプト内でブラウザが開く。ログイン後に自動で認証確認まで完了する。
スクリプトの「メタデータを取得しますか？」には **N** を入力する（次のステップで /sf-package が担当するため）。

## Step 3: 完了案内

認証完了後、以下を伝える:

```
認証完了。次のコマンドを実行してください:
  /sf-package  — メタデータを取得して資料を作成します
```
