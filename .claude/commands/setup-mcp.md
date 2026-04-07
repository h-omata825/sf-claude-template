---
description: "MCP（外部ツール連携）のセットアップ。Backlog・GitHub・Slack等の連携を設定する。"
---

## Step 1: 設定するMCPを選択

AskUserQuestion ツールを使い、以下をクリック選択式で提示する:

- `backlog` — Backlogチケット管理
- `github` — GitHub PR・Issue連携
- `slack` — Slackメッセージ送受信
- `notion` — Notionページ読み書き
- `playwright` — ブラウザ操作・UI自動テスト
- `show` — 現在の設定を確認

## Step 2: 実行

選択に応じてスクリプトを実行する:

```bash
bash scripts/setup-mcp.sh <選択したMCP>
```

例:
- `backlog` 選択: `bash scripts/setup-mcp.sh backlog`
- `show` 選択: `bash scripts/setup-mcp.sh show`

スクリプトがドメイン・トークン等を対話形式で入力させる。

## 完了後

「Claude Code を再起動すると設定が反映されます」と案内する。

## 注意

- トークン・APIキーをチャット上に表示・出力しない
- `.mcp.json` の内容をdocs/に記録しない
