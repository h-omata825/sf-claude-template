---
description: "Salesforce組織からメタデータを取得する。package.xml の生成と取得対象をクリック選択で指定できる。"
---

Salesforce組織からメタデータを取得してください。

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
# 例: Apex クラス MyClass・フロー MyFlow・オブジェクト Account を指定した場合
cat > manifest/package.xml << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types>
        <members>MyClass</members>
        <name>ApexClass</name>
    </types>
    <types>
        <members>MyFlow</members>
        <name>Flow</name>
    </types>
    <types>
        <members>Account</members>
        <name>CustomObject</name>
    </types>
    <version>59.0</version>
</Package>
EOF

sf project retrieve start --manifest manifest/package.xml
```

メタデータタイプの対応表（主要なもの）:

| 指定内容 | `<name>` タグ |
|---|---|
| Apex クラス | `ApexClass` |
| Apex トリガー | `ApexTrigger` |
| フロー | `Flow` |
| LWC コンポーネント | `LightningComponentBundle` |
| オブジェクト・項目 | `CustomObject` |
| 権限セット | `PermissionSet` |
| カスタムメタデータ型 | `CustomMetadata` |

---

## Step 3: 完了報告

取得完了後、`docs/overview/org-profile.md` が存在するかチェックする。

**存在しない場合（初回）**:

AskUserQuestion で以下を表示する:

**質問**: 「メタデータの取得が完了しました。次のステップを選択してください。」

**選択肢**:
- `組織情報を収集する（/sf-memory）` — 推奨。組織情報を docs/ に記録する（初回はここまでやっておく）
- `外部ツール連携を先に設定する（/setup-mcp）` — Backlog・Notion・Slack 等と連携する場合
- `あとで` — ここで終了する

`組織情報を収集する` を選択した場合: /sf-memory を実行する
`外部ツール連携を先に設定する` を選択した場合: /setup-mcp を実行する（完了後に /sf-memory の実行を案内する）

**存在する場合（2回目以降）**:

取得後に git diff で変更内容を確認し、変更の種別に応じて以下を通知する:

```bash
git diff --name-only HEAD force-app/
```

変更ファイルを種別ごとに分類して以下の形式で通知する:

```
メタデータ取得完了。force-app/ に差分があります。

【変更検出】
- Apex / Flow / LWC / Trigger: {変更ファイル名一覧}
- オブジェクト定義 / 項目 / レイアウト / レコードタイプ: {変更ファイル名一覧}

【ドキュメント更新推奨】
① Apex / Flow / LWC 変更あり → /sf-memory カテゴリ4
   対象コンポーネント: {api_name一覧}
   完了後: 影響するFGの詳細設計・プログラム設計書の再生成を推奨

② オブジェクト / 項目 / レイアウト / レコードタイプ変更あり → /sf-memory カテゴリ2
   対象オブジェクト: {オブジェクト名一覧}
   完了後: 影響するFGの詳細設計・プログラム設計書の再生成を推奨
```

変更がない場合は「メタデータ取得完了。差分はありません。」とだけ伝える。
