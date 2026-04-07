---
description: "MCP（外部ツール連携）のセットアップ。GitHub・Slack・Notion等の連携を設定する。"
---

assistantエージェントとして、MCP（外部ツール連携）の設定を行ってください。

## 概要

`scripts/setup-mcp.sh` を使って `.mcp.json` を生成・更新する。

## ユーザー入力

$ARGUMENTS

## 実行

### 引数がある場合（直接指定）

```bash
bash scripts/setup-mcp.sh $ARGUMENTS
```

### 引数がない場合（対話モード）

```bash
bash scripts/setup-mcp.sh
```

スクリプトが対話的にMCPの選択とトークン入力を行う。

### 現在の設定を確認したい場合

```bash
bash scripts/setup-mcp.sh show
```

## 実行後

1. 結果をユーザーに伝える
2. 「Claude Code を再起動すると設定が反映されます」と案内する

## 注意事項

- トークンをチャット上に表示・出力しない
- トークンの値を docs/ に記録しない
