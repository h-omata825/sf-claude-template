---
description: "Salesforce組織からメタデータを取得する。package.xml の生成と取得対象をクリック選択で指定できる。"
---

salesforce-devエージェントとして、Salesforce組織からメタデータを取得してください。

## ユーザー入力

$ARGUMENTS

---

## Step 1: 取得対象の選択

引数がある場合はそれを「指定する」として解釈し、Step 2 の「指定する」の処理へ進む。

引数がない場合、AskUserQuestion ツールを使いクリック選択式で提示する:

- `standard` — 標準セット（Apex・フロー・オブジェクト・LWC等、開発でよく使うもの）
- `all` — 全メタデータ（時間がかかる）
- `select` — 取得するメタデータ名を個別に指定する

---

## Step 2: 実行

### 「standard」の場合

```bash
bash scripts/sf-retrieve.sh standard
```

### 「all」の場合

```bash
bash scripts/sf-retrieve.sh all
```

### 「select」の場合

取得したいメタデータ名（クラス名・フロー名・オブジェクト名等）をユーザーに確認する。
指定された名前からメタデータタイプを判定し `manifest/package.xml` を生成して取得する:

```bash
sf project retrieve start --manifest manifest/package.xml
```

---

## Step 3: 完了報告

取得完了後、`docs/overview/org-profile.md` が存在するかチェックする。

**存在しない場合（初回）**:

AskUserQuestion で以下を表示する:

**質問**: 「メタデータの取得が完了しました。続けて組織情報の収集（/sf-memory）を行いますか？初回は実行することを推奨します。」

**選択肢**:
- `実行する` — そのまま /sf-memory を実行する
- `あとで` — ここで終了する

**存在する場合（2回目以降）**:

以下のみ伝えて終了する:

```
メタデータ取得完了。force-app/ に保存されました。
```
