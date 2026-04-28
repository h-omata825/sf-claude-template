# option-permission-fls-check

## 何をするか

権限セット・プロファイル・FLS（Field-Level Security）への影響を確認する。課題の原因または修正の影響として権限が関与していないか調査する。

## 実行手順

1. 変更対象のフィールド・オブジェクトを確定する
2. FLS 設定を確認する:
   ```bash
   # 権限セットの FLS 設定を確認
   Grep pattern: {フィールド API 名}
   ファイル: force-app/main/default/permissionsets/**/*.xml
   ```
3. プロファイルの FLS 設定を確認する:
   ```bash
   Grep pattern: {フィールド API 名}
   ファイル: force-app/main/default/profiles/**/*.profile-meta.xml
   ```
4. 対象フィールドが以下のどのアクセスを持つか確認する:
   - `readable: true / false`
   - `editable: true / false`
5. 課題の症状（見えない・保存できない・エラーになる）と FLS の関係を評価する:
   - FLS が原因の場合 → 修正方針を「FLS 設定変更」方向に更新
   - FLS は無関係の場合 → 「FLS 確認済み・無関係」と記録
6. 修正で新規フィールドを追加する場合は、必要な権限セット・プロファイルのデフォルト設定を検討する

## 出力

investigation.md「影響範囲」または「根本原因」セクションに追記:

| 権限セット / プロファイル | フィールド | Readable | Editable | 影響判定 |
|---|---|---|---|---|
| ... | ... | true / false | true / false | 原因 / 無関係 / 要修正 |
