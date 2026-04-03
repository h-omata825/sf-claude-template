assistantエージェントとして、MCP（外部ツール連携）の設定を行ってください。
新規作成と既存設定の更新の両方に対応する。

## 動作モード判定

1. `.mcp.json` の存在を確認する
   - **存在しない** → 新規作成モード
   - **存在する** → 更新モード

---

## 新規作成モード

### Step 1: MCP選択

ユーザーに使用するMCPを聞く:

```
使用するMCPを選んでください（複数可、カンマ区切り）:

  github     — GitHubリポジトリ操作・PRレビュー連携
  slack      — Slackメッセージ送受信
  gdrive     — Google Driveファイルアクセス
  notion     — Notionページ読み書き
  playwright — ブラウザ操作・UI自動テスト
  なし       — MCPを使わない（後で /setup-mcp で追加可能）

例: github, slack
```

「なし」の場合 → 全MCP無効の `.mcp.json` を生成して完了。

### Step 2: トークン入力

選択された各MCPについて、1つずつトークンの入力を求める。

#### github
```
GitHub Personal Access Token を入力してください。
取得方法: GitHub → Settings → Developer settings → Personal access tokens → Generate new token
必要なスコープ: repo, read:org

トークン:
```

#### slack
```
Slack Bot Token を入力してください（xoxb- で始まるもの）。
取得方法: PM/管理者から案内されたSlack App管理画面で確認

トークン:
```

#### gdrive
```
Google OAuth Client ID を入力してください。
取得方法: Google Cloud Console → APIとサービス → 認証情報

Client ID:
```
続けて:
```
Google OAuth Client Secret を入力してください。

Client Secret:
```

#### notion
```
Notion Integration Token を入力してください（ntn_ で始まるもの）。
取得方法: Notion → Settings → Connections → Develop or manage integrations

トークン:
```

#### playwright
トークン不要。有効化するだけ。

### Step 3: .mcp.json 生成

以下のテンプレートをもとに `.mcp.json` を生成する。
選択されたMCPはトークンを埋め込んで有効化、選択されなかったMCPは `"disabled": true` で無効化。

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "<TOKEN>"
      },
      "disabled": true
    },
    "slack": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-server-slack"],
      "env": {
        "SLACK_BOT_TOKEN": "<TOKEN>"
      },
      "disabled": true
    },
    "google-drive": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-server-gdrive"],
      "env": {
        "GOOGLE_CLIENT_ID": "<CLIENT_ID>",
        "GOOGLE_CLIENT_SECRET": "<CLIENT_SECRET>"
      },
      "disabled": true
    },
    "notion": {
      "command": "npx",
      "args": ["-y", "@notionhq/notion-mcp-server"],
      "env": {
        "OPENAPI_MCP_HEADERS": "{\"Authorization\": \"Bearer <TOKEN>\", \"Notion-Version\": \"2022-06-28\"}"
      },
      "disabled": true
    },
    "playwright": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-server-playwright"],
      "disabled": true
    }
  }
}
```

有効化するMCPの処理:
- `"disabled": true` の行を削除
- `<TOKEN>` 等のプレースホルダーを入力値に置換

---

## 更新モード

既存の `.mcp.json` がある場合。

### Step 1: 現在の状態を表示

`.mcp.json` を読み込んで現在の有効/無効状態を表示する:

```
現在のMCP設定:
  ✅ github     — 有効（トークン設定済み）
  ⬚ slack      — 無効
  ✅ notion     — 有効（トークン設定済み）
  ⬚ gdrive     — 無効
  ⬚ playwright — 無効

何をしますか？
  追加    — 新しいMCPを有効化する
  変更    — 既存のトークンを更新する
  削除    — MCPを無効化する
  終了    — 変更なし
```

### Step 2: 操作に応じて処理

#### 「追加」の場合
- 現在無効のMCP一覧を表示
- 有効化するMCPを選択してもらう
- トークンを入力してもらう（新規作成モードのStep 2と同じ）
- `.mcp.json` を更新

#### 「変更」の場合
- 現在有効のMCP一覧を表示
- 更新するMCPを選択してもらう
- 新しいトークンを入力してもらう
- `.mcp.json` を更新

#### 「削除」の場合
- 現在有効のMCP一覧を表示
- 無効化するMCPを選択してもらう
- 該当MCPに `"disabled": true` を追加
- `.mcp.json` を更新

### Step 3: 確認

更新後の状態を表示して完了。

---

## 完了メッセージ

```
.mcp.json を{作成/更新}しました。

有効なMCP:
  ✅ github
  ✅ slack
  （有効なもののみ表示）

※ .mcp.json は .gitignore 対象のため、Gitにはpushされません。
※ Claude Codeを再起動すると設定が反映されます。
※ 後からMCPを追加・変更・削除したい場合は /setup-mcp を再実行してください。
```

## 注意事項
- トークンは `.mcp.json` にのみ保存される（Git管理外）
- トークンをチャット上に表示・出力しない
- `.mcp.json` に存在しないMCPサーバーの設定が追加された場合（テンプレートアップグレード等で新MCPが増えた場合）、上記テンプレートの定義を参照して追加する
