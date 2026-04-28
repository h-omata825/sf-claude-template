# option-impact-scope-grep

## 何をするか

変更対象に関係する Validation Rule・承認プロセス・割り当てルール・共通ユーティリティへの影響を Grep で網羅確認する。

## 実行手順

1. 変更するフィールド名・オブジェクト名を確定する
2. 以下を順番に Grep で確認する:

   **入力規則（Validation Rule）**:
   ```
   Grep pattern: {フィールド名 or オブジェクト名}
   ファイル: *.validationRule-meta.xml
   ```
   ヒットした場合は XML を Read してロジックへの影響を確認する

   **承認プロセス**:
   ```
   Grep pattern: {フィールド名 or オブジェクト名}
   ファイル: *.approvalProcess-meta.xml
   ```

   **割り当てルール**:
   ```
   Grep pattern: {フィールド名 or オブジェクト名}
   ファイル: *.assignmentRules-meta.xml
   ```

   **共通ユーティリティ**:
   - CommonUtil / Utils 系クラスを Grep して変更対象を使用しているか確認

3. ヒットした各箇所を Read して影響を判定する

## 出力

investigation.md「影響範囲」セクションに追記:

| メタデータ種別 | ファイルパス | 影響判定 | 対応要否 |
|---|---|---|---|
| ValidationRule | ... | 影響あり / なし | 要 / 不要 |
| ApprovalProcess | ... | ... | ... |
