---
description: "package.xml を生成してメタデータを取得する。取得対象を対話形式で確認する。"
---

salesforce-devエージェントとして、package.xml を生成してメタデータを取得してください。

## ユーザー入力

$ARGUMENTS

---

## Step 1: 取得対象の確認

引数がある場合はそれを「指定する」として解釈し、Step 2 の「指定する」の処理へ進む。

引数がない場合、以下を提示してユーザーに選択させる:

```
取得するメタデータを選んでください:

  1. 指定する  — クラス名・フロー名・オブジェクト名を指定
  2. 標準セット — 開発でよく使うメタデータを一括取得
  3. 全て      — 組織の全メタデータを取得（時間がかかります）
```

---

## Step 2: 実行

### 「標準セット」の場合

スクリプトで一括実行:

```bash
bash scripts/sf-package.sh standard
```

### 「全て」の場合

スクリプトで一括実行:

```bash
bash scripts/sf-package.sh all
```

### 「指定する」の場合

この場合はスクリプトではなく Claude が対応する。

1. ユーザーに取得したいメタデータ名を聞く（クラス名・フロー名・オブジェクト名等）
2. 指定された名前からメタデータタイプを判定する
3. `manifest/package.xml` を直接生成する（APIバージョンは `sfdx-project.json` に合わせる）
4. 取得を実行:
   ```bash
   sf project retrieve start --manifest manifest/package.xml
   ```

---

## Step 3: 完了報告

取得完了後、以下を伝える:

```
メタデータ取得完了。force-app/ に保存されました。

次にできること:
  /sf-analyze  — 組織を解析して資料を自動生成
  /sf-catalog  — オブジェクト定義書を作成
  /sf-design   — 設計書を作成
```
