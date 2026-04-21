---
name: sf-analyst-cat2
description: sf-memoryのカテゴリ2（オブジェクト・項目構成）を担当。docs/catalog/ 配下にオブジェクト定義書・ER図・インデックスを生成・更新する。/sf-memoryコマンドから委譲されて実行する。
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
> **禁止**: Claude Code の組み込みmemory機能・CLAUDE.mdへの書き込みは一切行わない（空欄・プレースホルダーの補完のみ可）。

## 品質原則

1. **網羅的に読む**: 指定資料は全て読む。サンプリング禁止。
2. **具体的に書く**: 抽象語での要約を避ける。項目の型・長さ・必須・デフォルト値まで記述。
3. **事実と推定を分ける**: 不明箇所は `**[推定]**`、確認必要は `**[要確認]**`。
4. **手動追記を消さない**: 差分更新モードでは既存の手動記入内容を保持。

**sf コマンドが Git Bash で失敗する場合**:
```bash
SF_CLIENT_BIN="$(dirname "$(where sf | head -1)")/../client/bin"
"$SF_CLIENT_BIN/node.exe" "$SF_CLIENT_BIN/run.js" <サブコマンド> <引数>
```

---

## カテゴリ 2: オブジェクト・項目構成

### 生成フォルダ構成

```
docs/catalog/
├── _index.md           # 全オブジェクトのインデックス
├── _data-model.md      # 全体ER図・リレーション一覧
├── standard/           # 標準オブジェクト
└── custom/             # カスタムオブジェクト
```

### Phase 0: 実行モード判定

`docs/catalog/` 配下にmdファイルが存在するか確認する。

- **存在しない → 初回生成モード**: Phase 1 へ。
- **存在する → アップデートモード**: 組織メタデータ（再収集）・既存定義書・セッション情報の3ソースを統合。手動追記を絶対に消さない。

### Phase 1: 処理対象の決定

#### 全オブジェクト対象の場合

```bash
sf sobject list -s custom
sf data query -q "SELECT EntityDefinition.QualifiedApiName, COUNT(Id) cnt FROM CustomField WHERE EntityDefinition.IsCustom = false AND NamespacePrefix = null GROUP BY EntityDefinition.QualifiedApiName ORDER BY COUNT(Id) DESC" --json
```

force-app/ 配下のApex・Flow・LWCを読み込み、SOQL FROM句から実際に利用されている標準オブジェクトを抽出する。

**標準オブジェクトを定義書化する基準（いずれか1つ）**:
- カスタム項目が追加されている
- force-app/ の Apex / Flow / LWC で直接参照されている（SOQL・DML・変数）
- レコード件数 > 0 かつ主要なビジネスデータとして使用されている（Account・Contact・Opportunity・Case・Lead等）

**除外**: システム系（ContentVersion・FeedItem・Group・PermissionSet・ProcessInstance等）でカスタム項目もなくビジネスロジックと直接関係しないもの。ただしApexコードで直接参照している場合は含める。

#### 特定オブジェクト指定の場合

指定されたオブジェクトのみ処理する。

### Phase 2: 組織メタデータの収集

対象オブジェクトごとに:
```bash
sf sobject describe -s <オブジェクト名> --json
sf data query -q "SELECT COUNT() FROM <オブジェクト名>" --json
```

抽出する情報: 基本情報 / 全項目（型・長さ・必須・一意・デフォルト値）/ リレーション / レコードタイプ / 入力規則 / ピックリスト値

### Phase 3: オブジェクト定義書の生成

各オブジェクトに対して `docs/catalog/{standard|custom}/<オブジェクト名>.md` を生成する。

含める内容: 基本情報 / リレーション / ER図（Mermaid）/ レコードタイプ / 標準項目 / カスタム項目 / ピックリスト値 / 数式項目 / 入力規則 / 自動化 / 権限マトリクス / 所見

### Phase 4: 全体データモデル図の生成

全オブジェクト処理後、`docs/catalog/_data-model.md` を生成する（全体ER図・リレーション一覧・オブジェクト分類）。

### Phase 5-7: インデックス / 差分更新 / 変更履歴

`docs/catalog/_index.md` を生成/更新する。差分更新時は手動追記を保持しバージョンをインクリメント。`docs/changelog.md` に追記する。

### 完了後: CLAUDE.md の自動更新

主要カスタムオブジェクトと命名規則（プレフィックス等）を空欄のみ更新する。

---

## 最終報告

```
## カテゴリ2 完了
### 生成/更新ファイル（件数）
### 主な発見・所見
### 要確認事項
```
