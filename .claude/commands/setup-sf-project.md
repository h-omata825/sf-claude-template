---
description: "Salesforce + Claude Code プロジェクトの新規セットアップ。対話的にプロジェクト作成・テンプレート配置・組織認証まで一括実行する。"
---

Salesforce + Claude Code の新規プロジェクトをセットアップします。

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

### 1-3. 組織認証
```
接続するSalesforce組織の種別を入力してください
  prod   — 本番/Developer Edition（login.salesforce.com）
  dev    — Sandbox（test.salesforce.com）
  skip   — 後で設定する
  その他 — カスタムエイリアス（本番として認証）
```

---

## Step 2: 確認

ヒアリング内容をまとめて表示し、確認を取る:

```
以下の内容でセットアップします。よろしいですか？

  フォルダ名: <フォルダ名>
  作成先: <作成先パス>/<フォルダ名>
  組織: <種別> / エイリアス: <エイリアス>（またはスキップ）

（はい / いいえ）
```

「いいえ」の場合はどこを修正したいか聞いて、該当の質問だけやり直す。

---

## Step 3: セットアップ実行

`scripts/setup.sh` でプロジェクト作成を行う:

```bash
bash scripts/setup.sh <フォルダ名> "<作成先パス>"
```

---

## Step 4: 組織認証（skipでなければ）

プロジェクトフォルダに移動してから `scripts/setup-sf-project.sh` を実行:

```bash
cd "<作成先パス>/<フォルダ名>" && bash scripts/setup-sf-project.sh <エイリアス> <sandbox指定>
```

引数:
- `prod` の場合: `bash scripts/setup-sf-project.sh prod`
- `dev` の場合: `bash scripts/setup-sf-project.sh dev`
- カスタムエイリアスの場合: `bash scripts/setup-sf-project.sh <alias>`
- `skip` の場合: このステップをスキップ

---

## Step 5: プロジェクトフォルダを開く

VSCode内から実行している場合:
```bash
code --reuse-window "<作成先パス>/<フォルダ名>"
```

失敗した場合は新しいウィンドウで:
```bash
code "<作成先パス>/<フォルダ名>"
```

それも失敗した場合:
```
VSCodeの「ファイル > フォルダーを開く」から以下のパスを開いてください:
<作成先パス>/<フォルダ名>
```

---

## Step 6: 完了報告

```
============================================
  セットアップ完了！
============================================

プロジェクト: <作成先パス>/<フォルダ名>
組織: <エイリアス>（認証済み / 未設定）

やること:
  1. CLAUDE.md を開いてプロジェクト固有情報を記入
  2. /setup-mcp を実行してMCP連携を設定（必要な場合）
```
