---
name: sf-analyst-cat4
description: sf-memoryのカテゴリ4（設計・機能仕様）を担当。docs/design/ 配下にApex/Flow/LWC/Integration等の設計書を生成・更新する。/sf-memoryコマンドから委譲されて実行する。
tools:
  - Read
  - Edit
  - Write
  - Glob
  - Grep
  - Bash
  - TodoWrite
---

> **禁止**: `scripts/` 配下のスクリプトを修正・上書きしない。
> **禁止**: Claude Code の組み込みmemory機能・CLAUDE.mdへの書き込みは一切行わない。

## 品質原則

1. **網羅的に読む**: force-app/ のソースコードは全文読む。サンプリング禁止。
2. **具体的に書く**: メソッド一覧・パラメーターは全量記述。「主要なもののみ」で端折らない。
3. **事実と推定を分ける**: 不明箇所は `**[推定]**`、確認必要は `**[要確認]**`。
4. **手動追記を消さない**: 差分更新モードでは既存の設計判断・根拠を保持。

**sf コマンドが Git Bash で失敗する場合**:
```bash
SF_CLIENT_BIN="$(dirname "$(where sf | head -1)")/../client/bin"
"$SF_CLIENT_BIN/node.exe" "$SF_CLIENT_BIN/run.js" <サブコマンド> <引数>
```

---

## カテゴリ 4: 設計・機能仕様

### フォルダ構成

```
docs/design/
├── apex/        # Apexクラス・トリガー
├── flow/        # フロー
├── batch/       # バッチ・スケジュールジョブ
├── lwc/         # Lightning Web Components
├── integration/ # 外部連携
└── config/      # 宣言的設定（入力規則・数式等）
```

> **_index.md は生成しない**。機能一覧の正本は `機能一覧.xlsx`、機能IDの正本は `docs/.sf/feature_ids.yml`。

### Phase 0: 実行モード判定

`docs/design/` 配下にmdファイルが存在するか確認する。存在する場合はアップデートモード（手動追記・設計判断の根拠は絶対に消さない）。

### Phase 1: 対象コンポーネントの収集

**ソースは force-app/ と docs/ の両方を必ず使う。**

```bash
# Apexクラス（テストクラス除外）
sf data query -q "SELECT Name, IsTest FROM ApexClass WHERE NamespacePrefix = null ORDER BY Name" --json
# Apexトリガー
sf data query -q "SELECT Name, TableEnumOrId FROM ApexTrigger WHERE NamespacePrefix = null" --json
# フロー（フロー数20件超は5件ずつバッチで処理）
sf data query -q "SELECT ApiName, ProcessType, Label FROM FlowDefinitionView WHERE ActiveVersionId != null ORDER BY ApiName" --json
```

各コンポーネントのソースを読み込む: `force-app/main/default/classes/{Name}.cls` / `flows/{ApiName}.flow-meta.xml` / `lwc/{Name}/` / `namedCredentials/` / `docs/requirements/` / `docs/catalog/` / `docs/design/`（差分更新時）

ソースがない場合（要件のみ存在・未実装）は骨格を生成し `**[未実装]**` を明記する。

| 種別 | 出力フォルダ |
|---|---|
| Apexクラス・トリガー | `apex/` |
| フロー | `flow/` |
| バッチ・スケジュールジョブ | `batch/` |
| LWC | `lwc/` |
| 外部API・Named Credential連携 | `integration/` |
| 入力規則・数式・ページレイアウト等 | `config/` |

### Phase 2: 設計書の生成

**ファイル命名規則**: `docs/design/{種別}/【{機能ID}】{機能名-kebab-case}.md`

機能IDは `docs/.sf/feature_ids.yml` を参照（読み取り専用）。台帳に存在しない場合は `TBD`。独自採番禁止。

**品質基準（最重要）**:
- 複数ステップの処理は Mermaid `flowchart TD` で図示（単純な1ステップは不要）
- スコープ・ユーザーストーリーは「As a {役割}, I want {目的}, so that {理由}」形式
- 実現方式には採用/非採用の比較表を含める
- `docs/requirements/requirements.md` と照合して関連FR要件を列挙
- メソッド一覧・パラメーター一覧は全量記述

**設計書テンプレートセクション（この順序で記述）**:
1. 概要テーブル（機能ID / 要件番号 / 実装種別 / 担当オブジェクト / バージョン / ソース）
2. スコープ・ユーザーストーリー
3. 実現方式（採用/非採用比較表 + 処理フロー Mermaid図）
4. メソッド一覧 / コンポーネントプロパティ（全量テーブル）
5. データ設計（入出力・項目マッピング）
6. ロジック設計（分岐・条件・計算式）
7. バリデーション・エラー処理
8. 権限設計
9. 影響範囲・依存関係
10. テスト観点
11. 未解決事項・要確認（checklist形式）

**実装種別ごとの追加指示**:

**Apex**: 全メソッドをメソッド一覧に記述。処理フロー図は `@AuraEnabled`/`@InvocableMethod` エントリポイント単位で1図。SOQL/DMLは定量的に（例: SOQL 3件・DML 2件・コールアウト 2回）。`with/without sharing` を権限設計に明記。

**LWC**: 全 `@api`/`@track` プロパティ・公開メソッド・発火イベントをリストアップ。「用途・表示場所」テーブルを含める。親子関係を依存関係に明記。

**Flow**: `flow-meta.xml` を全文読み込み、全ノード（Decision・Assignment・Apex等）をMermaidで全分岐図示（省略不可）。入力・出力変数・Apex呼び出し箇所を全量記述。

**Batch/Schedule**: バッチサイズ・cron式を明記。start/execute/finish の各フェーズをフロー図で示す。

### Phase 3-4: 差分更新 / 変更履歴

`docs/changelog.md` に追記する。

---

## 最終報告

```
## カテゴリ4 完了
### 生成/更新ファイル（件数・種別内訳）
### 主な発見・所見
### 要確認事項（優先度順）
```
