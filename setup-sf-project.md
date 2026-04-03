---
description: "Salesforce + Claude Code プロジェクトの新規セットアップ。対話的にプロジェクト作成・テンプレート配置・組織認証まで一括実行する。"
---

Salesforce + Claude Code の新規プロジェクトをセットアップします。
以下の手順を順番に実行してください。

---

## 事前チェック

まず以下のコマンドを実行して、必要なツールがインストールされているか確認する:

```bash
sf --version
git --version
```

- `sf` が見つからない場合 → 「Salesforce CLIがインストールされていません。 https://developer.salesforce.com/tools/salesforcecli からインストールしてください」と案内して中断
- `git` が見つからない場合 → 「Gitがインストールされていません」と案内して中断

---

## Step 1: ヒアリング

ユーザーに以下を **1つずつ** 質問する。前の回答を得てから次を聞く。
**全ての質問はテキスト入力（自由記述）で回答してもらう。選択肢UIは絶対に使わない。AskUserQuestionのoptionsパラメータは使用禁止。**

### 1-1. フォルダ名
```
作成するプロジェクトのフォルダ名を入力してください（英語）
例: myProject, sales-portal, CaseManagement
```

### 1-2. 作成先パス
```
プロジェクトフォルダの作成先パスを入力してください
例: C:/workspace, D:/projects
```
- 入力されたパスが存在するか `test -d` で確認する
- 存在しなければ「そのフォルダは存在しません。作成しますか？」と聞く
- 作成先パス + フォルダ名 が既に存在する場合「既に存在します。別のフォルダ名を入力してください」と聞き直す

### 1-3. テンプレートURL
```
使用するテンプレートのGitリポジトリURLを入力してください
デフォルト: https://github.com/h-omata825/sf-claude-template.git
（デフォルトでよければ「デフォルト」と入力してください）
```
- 「デフォルト」と入力された場合はデフォルト値を使う
- それ以外はそのままURLとして使う

### 1-4. 組織認証
```
接続するSalesforce組織の種別を入力してください
  本番 — 本番/Developer Edition（login.salesforce.com）
  開発 — Sandbox（test.salesforce.com）
  スキップ — 後で設定する
```
- 「本番」の場合 → エイリアスは自動で「prod」に設定。次のステップへ進む
- 「開発」の場合 → エイリアスは自動で「dev」に設定。次のステップへ進む
- 上記以外の文字列が入力された場合 → その文字列をエイリアス名として使用し、本番（login.salesforce.com）で認証する

---

## Step 2: 確認

ヒアリング内容をまとめて表示し、確認を取る:

```
以下の内容でセットアップします。よろしいですか？

  フォルダ名: <フォルダ名>
  作成先: <作成先パス>/<フォルダ名>
  テンプレート: <URL>
  組織: <種別> / エイリアス: <エイリアス>（またはスキップ）

（はい / いいえ）
```

「いいえ」の場合はどこを修正したいか聞いて、該当の質問だけやり直す。

---

## Step 3: プロジェクト作成

以下のコマンドを順番に実行する。各ステップの完了を確認してから次に進む。

### 3-1. SFDXプロジェクト作成
```bash
sf project generate -n <フォルダ名> -d "<作成先パス>" --manifest
```

### 3-2. テンプレート取得・配置
```bash
git clone <テンプレートURL> "<作成先パス>/<フォルダ名>/.claude-template-tmp"
```

```bash
cp -r "<作成先パス>/<フォルダ名>/.claude-template-tmp/.claude" "<作成先パス>/<フォルダ名>/.claude"
cp "<作成先パス>/<フォルダ名>/.claude-template-tmp/CLAUDE.md" "<作成先パス>/<フォルダ名>/CLAUDE.md"
cp -r "<作成先パス>/<フォルダ名>/.claude-template-tmp/docs" "<作成先パス>/<フォルダ名>/docs"
cp "<作成先パス>/<フォルダ名>/.claude-template-tmp/.mcp.json.example" "<作成先パス>/<フォルダ名>/.mcp.json.example"
cp "<作成先パス>/<フォルダ名>/.claude-template-tmp/upgrade.sh" "<作成先パス>/<フォルダ名>/upgrade.sh"
```

### 3-3. クリーンアップ
テンプレート取得用の一時フォルダを削除する。プロジェクトフォルダの中にあるので安全。
```bash
rm -r "<作成先パス>/<フォルダ名>/.claude-template-tmp"
```

### 3-4. .gitignore 更新
```bash
echo "" >> "<作成先パス>/<フォルダ名>/.gitignore"
echo "# Claude Code（個人設定）" >> "<作成先パス>/<フォルダ名>/.gitignore"
echo ".claude/settings.json" >> "<作成先パス>/<フォルダ名>/.gitignore"
echo ".mcp.json" >> "<作成先パス>/<フォルダ名>/.gitignore"
```

各コマンドでエラーが出た場合:
- sf project generate 失敗 → エラー内容を表示して原因を説明
- clone失敗 → 「URLを確認してください。プライベートリポジトリの場合はGitの認証設定が必要です」

---

## Step 4: 組織認証（スキップでなければ）

```bash
cd "<作成先パス>/<フォルダ名>"
```

種別に応じて実行:
- 本番の場合: `sf org login web -a <エイリアス>`
- 開発の場合: `sf org login web -a <エイリアス> -r https://test.salesforce.com`

ユーザーに伝える:
```
ブラウザが開きます。Salesforceにログインしてください。
ログインが完了したらこちらに戻ってきてください。
```

認証完了後に確認:
```bash
sf org display -o <エイリアス>
```

成功したら、プロジェクトのデフォルト組織に設定する:
```bash
cd "<作成先パス>/<フォルダ名>" && sf config set target-org <エイリアス>
```

「組織の認証が完了し、デフォルト組織に設定しました」と伝える。
失敗したら「認証に問題がありました。もう一度試しますか？」と聞く。

---

## Step 5: メタデータ取得（組織認証済みの場合のみ）

ユーザーに聞く:
```
組織のメタデータを取得しますか？
package.xml を自動生成して、コードやメタデータを一括取得します。
（はい / いいえ）
```

「はい」の場合:

### 5-1. 組織のメタデータ一覧を取得
```bash
sf org list metadata-types -o <エイリアス> --json
```

### 5-2. package.xml を生成
取得した一覧をもとに、以下の主要メタデータを含む `manifest/package.xml` を生成する:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types>
        <members>*</members>
        <name>ApexClass</name>
    </types>
    <types>
        <members>*</members>
        <name>ApexTrigger</name>
    </types>
    <types>
        <members>*</members>
        <name>LightningComponentBundle</name>
    </types>
    <types>
        <members>*</members>
        <name>FlexiPage</name>
    </types>
    <types>
        <members>*</members>
        <name>Flow</name>
    </types>
    <types>
        <members>*</members>
        <name>CustomObject</name>
    </types>
    <types>
        <members>*</members>
        <name>CustomField</name>
    </types>
    <types>
        <members>*</members>
        <name>Layout</name>
    </types>
    <types>
        <members>*</members>
        <name>PermissionSet</name>
    </types>
    <types>
        <members>*</members>
        <name>Profile</name>
    </types>
    <types>
        <members>*</members>
        <name>ValidationRule</name>
    </types>
    <types>
        <members>*</members>
        <name>Workflow</name>
    </types>
    <version>62.0</version>
</Package>
```

**注意**: API バージョンは `sf org display` の結果から取得した値を使う。
上記はデフォルト構成。ユーザーに「この内容でよいですか？追加・削除したいメタデータはありますか？」と確認する。

### 5-3. メタデータ取得
```bash
sf project retrieve start -x manifest/package.xml -o <エイリアス>
```

取得結果を報告する。エラーがあれば内容を説明する。

---

## Step 6: プロジェクトフォルダを開く

VSCode内から実行している場合、`code` コマンドではなく VSCode API を使ってフォルダを開く:
```bash
code --reuse-window "<作成先パス>/<フォルダ名>"
```

上記が失敗した場合は、以下のコマンドで新しいウィンドウで開く:
```bash
code "<作成先パス>/<フォルダ名>"
```

それも失敗した場合は、ユーザーに伝える:
```
VSCodeの「ファイル > フォルダーを開く」から以下のパスを開いてください:
<作成先パス>/<フォルダ名>
```

---

## Step 7: 完了報告

```
============================================
  セットアップ完了！
============================================

プロジェクト: <作成先パス>/<フォルダ名>
組織: <エイリアス>（認証済み / 未設定）
メタデータ: 取得済み / 未取得

やること:
  1. CLAUDE.md を開いてプロジェクト固有情報を記入
     - プロジェクト概要
     - 主要オブジェクト
     - 命名規則
     - 注意事項

  2. .mcp.json のトークンを設定（必要な場合）
     - GitHub: Personal Access Token
     - Slack: Bot Token
     - Notion: Integration Token
```
