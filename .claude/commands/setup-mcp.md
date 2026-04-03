assistantエージェントとして、MCP（外部ツール連携）の初期設定を対話的に行ってください。

## 概要

`.mcp.json.example` をもとに `.mcp.json` を生成し、使用するMCPのトークンを設定する。

## 手順

### Step 1: 現状確認

1. `.mcp.json` が既に存在するか確認する
   - 存在する場合 → 「既に .mcp.json が存在します。上書きしますか？（はい/いいえ）」と確認
   - 「いいえ」の場合 → 中断
2. `.mcp.json.example` が存在するか確認する
   - 存在しない場合 → 「.mcp.json.example が見つかりません。テンプレートが正しく配置されているか確認してください」と案内して中断

### Step 2: MCP選択

ユーザーに使用するMCPを聞く:

```
使用するMCPを選んでください（複数可、カンマ区切り）:

  github     — GitHubリポジトリ操作・PRレビュー連携
  slack      — Slackメッセージ送受信
  gdrive     — Google Driveファイルアクセス
  notion     — Notionページ読み書き
  playwright — ブラウザ操作・UI自動テスト
  なし       — MCPを使わない（後で設定可能）

例: github, slack
```

「なし」の場合:
- `.mcp.json.example` を `.mcp.json` にコピー（全MCP無効のまま）
- 完了メッセージを表示して終了

### Step 3: トークン入力

選択された各MCPについて、1つずつトークンの入力を求める:

#### github を選択した場合
```
GitHub Personal Access Token を入力してください。
取得方法: GitHub → Settings → Developer settings → Personal access tokens → Generate new token
必要なスコープ: repo, read:org

トークン:
```

#### slack を選択した場合
```
Slack Bot Token を入力してください（xoxb- で始まるもの）。
取得方法: PM/管理者から案内されたSlack App管理画面で確認

トークン:
```

#### gdrive を選択した場合
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

#### notion を選択した場合
```
Notion Integration Token を入力してください（ntn_ で始まるもの）。
取得方法: Notion → Settings → Connections → Develop or manage integrations

トークン:
```

#### playwright を選択した場合
トークン不要。有効化するだけ。

### Step 4: .mcp.json 生成

1. `.mcp.json.example` を読み込む
2. 選択されたMCPについて:
   - `"disabled": true` の行を削除
   - トークンのプレースホルダー（`<YOUR_TOKEN>` 等）を入力されたトークンに置換
3. 選択されなかったMCPは `"disabled": true` のまま残す
4. `.mcp.json` として保存する

### Step 5: 確認

```
.mcp.json を作成しました。

有効化したMCP:
  ✅ github
  ✅ slack
  ⬚ gdrive（無効）
  ⬚ notion（無効）
  ⬚ playwright（無効）

※ .mcp.json は .gitignore に含まれるため、Gitにはpushされません。
※ Claude Codeを再起動すると設定が反映されます。
※ 後からMCPを追加/変更したい場合は /setup-mcp を再実行してください。
```

## 注意事項
- トークンは `.mcp.json` にのみ保存される（Git管理外）
- トークンをチャット上に表示しない（入力を受け取ったらマスクする）
- `.mcp.json.example` は変更しない（テンプレートとして維持）
