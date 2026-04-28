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
```

## Step 3: 認証

```bash
bash scripts/setup-sf-project.sh <alias>            # 本番の場合（login.salesforce.com）
bash scripts/setup-sf-project.sh <alias> sandbox    # Sandboxの場合（test.salesforce.com）
```

> **Sandbox の `--instance-url` について**: `sandbox` 引数を渡すと `https://test.salesforce.com` が自動で使われる。
> MyDomain（`https://xxx.sandbox.my.salesforce.com`）などカスタムURLを使う場合は、スクリプト実行後に `sf org login web --alias <alias> --instance-url <URL>` で上書きする。

スクリプト内でブラウザが開く。ログイン後に自動で認証確認まで完了する。
スクリプトの「メタデータを取得しますか？」には自動的に N が選択されます（/sf-retrieve が後続ステップで担当するため）。

## Step 4: 完了案内

### 4-1: 接続組織の種別を確認

```bash
sf org display --target-org <alias> --json
```

`isSandbox` フィールドを読み取り、ルートの `CLAUDE.md` に以下の形式で記録する（既存エントリがあれば上書き、なければ末尾に追加）:

```
<!-- sf-setup により自動記録 -->
接続組織: 本番 (alias: prod) — 初期セットアップ中。DML・デプロイ・force-app書き込み禁止
```

または

```
<!-- sf-setup により自動記録 -->
接続組織: Sandbox (alias: dev)
```

CLAUDE.md への記録完了後、以下をユーザーに提示する:

```
✅ 認証完了
  alias: {alias}
  種別: Sandbox / 本番
  default-org に設定済み（/backlog で使用される組織です）

別の組織も登録したい場合は再度 /sf-setup を実行してください。
default-org を切り替えるには: sf config set target-org <別alias>
```

### 4-2: 次のアクション分岐

`docs/` 配下に `.md` ファイルが存在するか確認する:

```bash
find docs -name "*.md" -type f 2>/dev/null | head -1
```

**docs/ にファイルが存在する場合（メンバーセットアップ）**:

組織情報・設計書はプロジェクトテンプレートに含まれています。すぐに作業を開始できます。

```
次のアクション（任意）:
- /setup-mcp  — Backlog・Notion・GitHub 等の外部ツール連携を設定する
```

**docs/ が空の場合（初期セットアップ）**:

AskUserQuestion ツールで以下を表示する:

**質問**: 「認証が完了しました。続けてメタデータの取得を行いますか？」

**選択肢**:
- `取得する` — そのまま /sf-retrieve を実行する
- `あとで` — 手順を案内して終了する

`取得する` の場合は /sf-retrieve を実行する。

`あとで` の場合は以下を案内して終了する:

```
初期セットアップの次のステップ:
1. /sf-retrieve  — メタデータを取得する（force-app/ に展開）
2. /sf-memory    — 組織情報を収集・記録する（docs/ を生成） ★本番接続中に実施
3. /sf-doc       — 設計書・定義書を生成する
4. CLAUDE.md     — プロジェクト固有情報を記入する
5. /setup-mcp    — 外部ツール連携（任意）

⚠️ 本番接続中（Step 2〜4）は読み取り操作のみです。
   データの変更・デプロイ・force-app への書き込みは行いません。
```
