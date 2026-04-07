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
bash scripts/sf-package.sh standard
```

### 「all」の場合

```bash
bash scripts/sf-package.sh all
```

### 「select」の場合

取得したいメタデータ名（クラス名・フロー名・オブジェクト名等）をユーザーに確認する。
指定された名前からメタデータタイプを判定し `manifest/package.xml` を生成して取得する:

```bash
sf project retrieve start --manifest manifest/package.xml
```

---

## Step 3: 完了報告

```
メタデータ取得完了。force-app/ に保存されました。

次にできること:
  /sf-analyze  — 組織を解析して資料を自動生成
  /sf-catalog  — オブジェクト定義書を作成
  /sf-design   — 設計書を作成
```
