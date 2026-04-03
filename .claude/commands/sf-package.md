---
description: "package.xml を生成してメタデータを取得する。取得対象を対話形式で確認する。"
---

salesforce-devエージェントとして、package.xml を生成してメタデータを取得してください。

## ユーザー入力

$ARGUMENTS

---

## Step 1: 取得対象の確認

以下を提示してユーザーに選択させる:

```
取得するメタデータを選んでください:

  1. 指定する  — クラス名・フロー名・オブジェクト名を指定
  2. 標準セット — 開発でよく使うメタデータを一括取得
               （ApexClass / ApexTrigger / Flow / CustomObject /
                 LightningComponentBundle / PermissionSet / CustomMetadata）
  3. 全て      — 組織の全メタデータを取得（時間がかかります）
```

引数がある場合はそれを「指定する」として解釈してStep 2へ進む。

---

## Step 2: package.xml の生成

選択に応じて `manifest/package.xml` を生成する。APIバージョンは `sfdx-project.json` に合わせる（なければ62.0）。

**「指定する」の場合:** 指定された名前からメタデータタイプを判定して生成する。

**「標準セット」の場合:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types><members>*</members><name>ApexClass</name></types>
    <types><members>*</members><name>ApexTrigger</name></types>
    <types><members>*</members><name>ApexPage</name></types>
    <types><members>*</members><name>Flow</name></types>
    <types><members>*</members><name>CustomObject</name></types>
    <types><members>*</members><name>CustomTab</name></types>
    <types><members>*</members><name>CustomLabel</name></types>
    <types><members>*</members><name>CustomMetadata</name></types>
    <types><members>*</members><name>CustomSetting</name></types>
    <types><members>*</members><name>LightningComponentBundle</name></types>
    <types><members>*</members><name>FlexiPage</name></types>
    <types><members>*</members><name>Layout</name></types>
    <types><members>*</members><name>PermissionSet</name></types>
    <types><members>*</members><name>PermissionSetGroup</name></types>
    <types><members>*</members><name>Profile</name></types>
    <types><members>*</members><name>StaticResource</name></types>
    <types><members>*</members><name>EmailTemplate</name></types>
    <types><members>*</members><name>ReportType</name></types>
    <types><members>*</members><name>Report</name></types>
    <types><members>*</members><name>Dashboard</name></types>
    <types><members>*</members><name>NamedCredential</name></types>
    <types><members>*</members><name>RemoteSiteSetting</name></types>
    <version>62.0</version>
</Package>
```

**「全て」の場合:** `sf org list metadata-types --target-org <alias>` で組織のメタデータタイプを取得してから全量の package.xml を生成する。

---

## Step 3: 取得実行

```bash
sf project retrieve start --manifest manifest/package.xml --target-org <alias>
```

取得先は `force-app/main/default/` 配下。**ローカルファイルを上書きするため、実行前に `git status` で現在の変更状況を確認する。**

---

## Step 4: 完了報告

```
取得完了。

取得したメタデータ: manifest/package.xml の内容に従って force-app/ に保存されました。

次のステップ:
  変更確認: git diff force-app/
  デプロイ準備: /sf-package で生成した package.xml をそのまま使用できます
```
