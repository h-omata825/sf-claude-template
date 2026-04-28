# Apex

## 種別選定（「Apex作って」と言われたら最初に用途を確認）

| 用途 | 推奨種別 |
|---|---|
| レコード保存時の処理 | トリガー + ハンドラークラス |
| 5万件超のバッチ処理 | `Database.Batchable` |
| 非同期・軽量処理 / チェーン実行 | `Queueable` |
| 定期実行（夜間バッチ等） | `Schedulable` |
| フローから呼び出す処理 | `@InvocableMethod` |
| 外部システムからのAPI受口 | `@RestResource` |
| 共通ロジックの切り出し | サービスクラス / ユーティリティクラス |

用途が複合している場合（例: 定期実行 + 大量データ）は `Schedulable` が `Database.Batchable` を呼び出す構成を提案する。

## トリガー設計

- **1オブジェクト1トリガー原則**を必ず守る（複数トリガーの実行順は保証されない）
- トリガー本体はロジックを持たず、全処理をハンドラークラスに委譲する
- before/after・insert/update/delete のどのイベントが必要か確認する
- 再帰防止が必要か確認する（static フラグ or TriggerHandler フレームワーク）

**既存自動化との競合チェック（必須）:**

トリガー作成・変更前に、対象オブジェクトの全自動化を洗い出す:
- 既存Apexトリガー（同一イベント）: `force-app/main/default/triggers/` で対象オブジェクトのトリガーを検索
- レコードトリガーフロー（実行順序: Apex before → Flow before → DB → Apex after → Flow after）: `force-app/main/default/flows/` で検索
- 入力規則（before save で評価）: `force-app/main/default/objects/*/validationRules/` で検索
- ワークフロールール・プロセスビルダー（レガシー。残存していれば警告）

1トリガー/1オブジェクトパターンに従っているか確認。複数トリガーが存在する場合は統合を提案。

## コーディング規約（常に適用）

- `with sharing` をデフォルト。意図的に無視する場合のみ `without sharing` / `inherited sharing`（理由をコメントで明記）
- SOQL・DML は必ずループ外に配置
- ハードコード禁止（レコードID・メールアドレス・組織固有の値等）→ カスタムメタデータ / カスタム設定を提案
- `Database.insert(records, false)` で部分成功を許容するか確認（デフォルトは全件失敗 `true`）
- FLS確認が必要な場合は `Security.stripInaccessible()` を使用

## テストクラス（実装とセットで必ず提供）

qa-engineer.md の「Apexテストクラス品質基準」に準拠する。外部コールアウトがある場合は `HttpCalloutMock` を実装してセットで提供すること。

## バッチ / Queueable / Scheduled の追加確認

**Batchable:**
- スコープサイズ（デフォルト200）を確認。大きすぎるとCPUタイムアウト、小さすぎると非効率
- 処理間で状態を保持する必要があれば `Database.Stateful` を提案（ヒープ消費に注意）
- エラーレコードの処理方針（スキップして続行 or 全件ロールバック）を確認

**Queueable:**
- チェーン実行の深さ制限（本番5回 / Sandbox無制限）を説明
- `Database.Batchable` との使い分け基準を説明（件数が少ない・チェーンが必要 → Queueable）

**Schedulable:**
- CRON式を提示してユーザーに確認（例: `0 0 2 * * ?` = 毎日午前2時）
- 同時実行が起きる可能性がある場合は排他制御（カスタム設定フラグ）を提案

## 変更時の影響調査

変更前に以下を調査して結果を提示する:
- 他Apexクラスからのメソッド呼び出し（Grep: クラス名 / メソッド名）
- フローの `Apex Action` での参照
- `@InvocableMethod` / `@AuraEnabled` / `@RestResource` として外部公開されているか（変更の影響範囲が広い）
- APIバージョン（古い場合は最新への更新を提案、ただし強制しない）
- 対応するテストクラスの更新が必要かどうかを確認

## エラーハンドリング

- `try-catch` は処理単位で適切に設定。例外を握りつぶして空の catch は禁止
- 同じ例外処理が複数箇所に出たらカスタム例外クラスの作成を提案
- エラー発生時の通知・記録方針（Platform Event / カスタムオブジェクトへのログ記録）をユーザーに確認
