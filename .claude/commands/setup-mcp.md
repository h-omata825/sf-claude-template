---
description: "GitHub連携（MCP）のセットアップ。PRレビュー・Issue管理等に使用。他のMCPもオプションで設定可能。"
---

assistantエージェントとして、MCP（外部ツール連携）の設定を行ってください。

## 概要

Salesforce開発で必要なMCPは **GitHub のみ**。
他（Slack、Google Drive 等）はオプション。必要に応じて追加できる。

---

## Phase 1: .mcp.json の状態確認

`.mcp.json` の存在を確認する。
- **存在しない** → Phase 2（GitHub 設定）へ
- **存在する** → 内容を読み込んで現在の状態を表示し、何をするか聞く:
  ```
  現在のMCP設定:
    github — 有効/無効
    （他に設定があれば表示）

  何をしますか？
    追加 — 新しいMCPを有効化
    変更 — トークンを更新
    削除 — MCPを無効化
  ```

---

## Phase 2: GitHub 設定（メイン）

```
GitHub Personal Access Token を入力してください。

取得方法:
  1. GitHub → 右上のアイコン → Settings
  2. 左メニュー最下部「Developer settings」
  3. Personal access tokens → Tokens (classic) → Generate new token
  4. 必要なスコープにチェック: repo, read:org
  5. Generate token → トークンをコピー

トークン:
```

入力されたトークンで `.mcp.json` を生成する:

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "<入力されたトークン>"
      }
    }
  }
}
```

---

## Phase 3: 追加MCP（オプション）

GitHub 設定後に聞く:
```
GitHub の設定が完了しました。

他に追加したいMCPはありますか？（不要なら「なし」）
  slack      — Slackメッセージ送受信（チーム通知用）
  gdrive     — Google Drive / スプレッドシートへのアクセス
  notion     — Notionページ読み書き
  playwright — ブラウザ操作
```

「なし」→ Phase 4（完了）へ。

### Slack を選択した場合
```
Slack Bot Token を入力してください（xoxb- で始まるもの）。
取得方法: PM/管理者から案内されたSlack App管理画面で確認

トークン:
```
→ `.mcp.json` に追加:
```json
"slack": {
  "command": "npx",
  "args": ["-y", "@anthropic/mcp-server-slack"],
  "env": {
    "SLACK_BOT_TOKEN": "<トークン>"
  }
}
```

### Google Drive を選択した場合
```
Google OAuth Client ID を入力してください。
取得方法: Google Cloud Console → APIとサービス → 認証情報

Client ID:
```
```
Google OAuth Client Secret を入力してください。

Client Secret:
```
→ `.mcp.json` に追加:
```json
"google-drive": {
  "command": "npx",
  "args": ["-y", "@anthropic/mcp-server-gdrive"],
  "env": {
    "GOOGLE_CLIENT_ID": "<Client ID>",
    "GOOGLE_CLIENT_SECRET": "<Client Secret>"
  }
}
```

### Notion を選択した場合
```
Notion Integration Token を入力してください（ntn_ で始まるもの）。
取得方法: Notion → Settings → Connections → Develop or manage integrations

トークン:
```
→ `.mcp.json` に追加:
```json
"notion": {
  "command": "npx",
  "args": ["-y", "@notionhq/notion-mcp-server"],
  "env": {
    "OPENAPI_MCP_HEADERS": "{\"Authorization\": \"Bearer <トークン>\", \"Notion-Version\": \"2022-06-28\"}"
  }
}
```

### Playwright を選択した場合
トークン不要。`.mcp.json` に追加:
```json
"playwright": {
  "command": "npx",
  "args": ["-y", "@anthropic/mcp-server-playwright"]
}
```

---

## Phase 4: 完了

```
.mcp.json を設定しました。

有効なMCP:
  - github（PR・Issue管理）
  （他に設定したものがあれば表示）

注意:
  - .mcp.json は .gitignore 対象のため Git にはpushされません
  - Claude Code を再起動すると設定が反映されます
  - 後から変更したい場合は /setup-mcp を再実行してください
```

## 注意事項
- トークンは `.mcp.json` にのみ保存される（Git管理外）
- トークンをチャット上に表示・出力しない
- トークンの値をログや docs/ に記録しない
