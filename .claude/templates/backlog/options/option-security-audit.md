# option-security-audit

## 何をするか

セキュリティ監査を実施する。CRUD / FLS の一括確認・SOQL インジェクション・XSS・with sharing の設定を確認する。

## 実行手順

1. 実装した Apex クラスの全てについて以下を確認する:

   **with sharing 宣言**:
   - `with sharing` または `without sharing` が明示されているか
   - 外部から呼ばれる Controller / Service クラスは `with sharing` が原則
   - `without sharing` を使う場合は意図的な理由をコメントで記述する

   **CRUD 確認**:
   - DML（insert / update / delete / upsert）前に Schema.sObjectType.{Object}.is{Action}able() を確認しているか
   - または FLS / CRUD チェックが不要な理由が明確か（システム処理・管理者専用等）

   **FLS 確認**:
   - ユーザーが直接操作する画面の Apex で FLS を考慮しているか
   - `Security.stripInaccessible()` の活用
   - または FLS チェックが不要な理由が明確か

   **SOQL インジェクション**:
   - 動的 SOQL（`Database.query(queryString)` 等）でユーザー入力を文字列連結していないか
   - 対策: `String.escapeSingleQuotes()` または Bind 変数の使用

   **XSS（出力エスケープ）**:
   - LWC / Aura でユーザー入力をそのまま `innerHTML` に代入していないか
   - VisualForce で `{!value}` （エスケープあり）を `{!HTMLENCODE(value)}` の代わりに使っているか

2. 問題を発見した場合はコードを修正する

## 出力

test-report.md に追記:

## セキュリティ監査結果

| 確認項目 | 対象 | 結果 | 対応 |
|---|---|---|---|
| with sharing | {クラス名} | 設定済み / 修正済み | ... |
| CRUD チェック | {DML 箇所} | OK / 修正済み | ... |
| FLS チェック | {フィールド} | OK / 修正済み | ... |
| SOQL インジェクション | {動的SOQL箇所} | なし / 修正済み | ... |
| XSS | {LWC/VF 箇所} | なし / 修正済み | ... |
