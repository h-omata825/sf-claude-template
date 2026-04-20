# スケルトンモード詳細仕様（sf-design-writer 参照用）

`extract_apex_skeleton.py` が生成したスケルトン JSON を受け取った場合のモード。

## スケルトンモードの見分け方

渡された JSON に `"_parser_meta"` フィールドが存在する場合 = スケルトンモード。

## スケルトンモードでの禁止事項

**以下のフィールドは変更してはならない（スクリプトが機械的に確定した値）:**

| フィールド | 理由 |
|---|---|
| `node_type` | Apex の制御構造から確定済み（if→decision, catch→error 等） |
| `calls` | 外部クラス呼び出しをコードから抽出済み |
| `object_ref` | SOQL の FROM 句・DML 対象から抽出済み |
| `branch` | if/try の構造から確定済み |
| `sub_steps[].title` | "SOQL" / "DML" は固定ラベル |
| `sub_steps[].detail` | 実際のクエリ・DML 文から抽出済み |
| `api_name` | クラス名から確定済み |

## スケルトンモードで記述するフィールド

| フィールド | 内容 |
|---|---|
| `name` | 機能名（日本語）。コードのコメント・クラス名から推定 |
| `overview.purpose` | 本書の目的 |
| `overview.trigger` | 処理契機（`@InvocableMethod` / スケジュール / トリガー等） |
| `overview.preconditions` | 前提条件 |
| `overview.summary` | 処理概要（エントリーから終了まで一気に説明） |
| 各 `steps[].method_name` | Apex メソッド名（例: `createQuote`）。タイトルには入れず、ここに書く |
| 各 `steps[].title` | そのステップが何をする処理か（日本語・15文字以内を目安。クラス名・メソッド名を含めない） |
| 各 `steps[].detail` | 詳細説明（日本語のみ。コード混入禁止） |
| `params.input[]` / `params.output[]` | パラメーター定義（型・必須・説明） |
| `_parser_meta` | **削除する**（出力 JSON には含めない） |

## スケルトンモードの手順

```
1. Apex ソースファイルを読む（ソースが渡されていない場合は force-app/ を探す）
2. スケルトン JSON の各ステップの sub_steps を確認し、ソースと照合する
3. title / detail を記述する（node_type 等は変更しない）
4. overview の型を確認する
   スケルトンの overview は {"purpose": "", "trigger": "", "preconditions": "", "summary": ""} の dict 形式。
   generate_feature_design.py（lines 508-514）が dict → string を自動変換するため、dict のまま保存しても動作する。
   ただし自動変換を待たず summary の文字列に置き換えておくとデバッグが容易:
     before: "overview": {"purpose": "...", "trigger": "...", "preconditions": "...", "summary": "処理概要テキスト"}
     after:  "overview": "処理概要テキスト"
5. name / params を記述する
6. _parser_meta フィールドを削除する
7. Phase 1.5 のチェックリストを実行する（structural フィールドの変更がないか確認）
8. Phase 2 へ進む（Excel 生成）
```

> **品質基準は同じ**。スケルトンモードでも「読んだものは全て書く」原則は変わらない。
> structural フィールドが既に埋まっているぶん、説明文の品質に集中できる。
