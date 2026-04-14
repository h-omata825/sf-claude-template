---
description: "Salesforce組織の認証を行う。setup.sh でプロジェクト作成後に実行する。"
---

## 事前チェック

```bash
sf --version && test -f sfdx-project.json && echo "OK"
```

失敗した場合: sfが無ければCLIインストールを案内、sfdx-project.jsonが無ければ「プロジェクトルートで実行してください」と伝えて終了。

## Step 1: 組織種別の選択

AskUserQuestion ツールを使い、以下をクリック選択式で提示する:

- `本番` — login.salesforce.com
- `Sandbox` — test.salesforce.com
- `skip` — 後で設定する

## Step 2: エイリアス名の入力

`skip` 以外の場合、エイリアス名を質問する:

```
組織のエイリアス名を入力してください
デフォルト候補: prod（本番の場合）/ dev（Sandboxの場合）
自由入力も可
```

## Step 3: 認証

```bash
bash scripts/setup-sf-project.sh <alias>            # 本番の場合
bash scripts/setup-sf-project.sh <alias> sandbox    # Sandboxの場合
```

スクリプト内でブラウザが開く。ログイン後に自動で認証確認まで完了する。
スクリプトの「メタデータを取得しますか？」には **N** を入力する（次のステップで /sf-retrieve が担当するため）。

## Step 3: 完了案内

認証完了後、AskUserQuestion ツールで以下を表示する:

**質問**: 「認証が完了しました。続けてメタデータの取得を行いますか？」

**選択肢**:
- `取得する` — そのまま /sf-retrieve を実行する
- `あとで` — ここで終了する（あとで /sf-retrieve を実行する）

`取得する` を選択した場合は、続けて /sf-retrieve コマンドを実行する。

`あとで` を選択した場合は、以下を案内して終了する:

```
セットアップの次のステップ:
1. /sf-retrieve   — メタデータの取得
2. /setup-mcp     — 外部ツール連携（任意: Backlog・Notion・Slack 等）
3. /sf-memory     — 組織情報の記録（初回は本番環境で実施推奨）
```
