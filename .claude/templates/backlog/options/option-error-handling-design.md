# option-error-handling-design

## 何をするか

エラーハンドリング設計をレビューする。例外伝播・ロールバック・ユーザー通知の整合性を確認する。

## 実行手順

1. 実装計画（implementation-plan.md）のエラーハンドリング部分を確認する
2. 以下の観点でレビューする:

   **例外の種類と補足**:
   - どの例外（DmlException / NullPointerException / CalloutException 等）を補足するか
   - try-catch の粒度が適切か（広すぎず・狭すぎず）
   - catch 節で何もしない（握りつぶし）になっていないか

   **ロールバック**:
   - DML エラー発生時に意図しない中途半端なデータ更新が残らないか
   - Savepoint / rollback の使用が必要なケースを考慮しているか
   - Database.insert(records, allOrNone) の allOrNone 設定が意図通りか

   **ユーザーへの通知**:
   - エラー時にユーザーが意味のあるメッセージを受け取れるか
   - Apex: addError() の活用 / AuraHandledException のスロー
   - LWC: エラー表示の UX（どこにどんなメッセージを出すか）
   - システム管理者向けのログ（Apex ログ・Platform Event 等）

   **外部連携（Callout）のエラー**:
   - HTTP 4xx / 5xx / タイムアウトのハンドリング
   - リトライロジックの有無
   - Callout 後の DML 制約（同一トランザクション内）

3. 不足・問題があれば implementation-plan.md に修正案を記録する

## 出力

implementation-plan.md に追記:

## エラーハンドリング設計レビュー

| 確認観点 | 現在の計画 | 評価 | 改善案 |
|---|---|---|---|
| 例外補足 | try-catch({例外型}) | 適切 / 要修正 | {修正案} |
| ロールバック | allOrNone=true | 適切 / 要修正 | ... |
| ユーザー通知 | addError() | 適切 / 要修正 | ... |
| Callout ハンドリング | {現在の設計} | 適切 / 要修正 | ... |
