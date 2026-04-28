# option-existing-test-baseline

## 何をするか

変更前の既存テスト状態を記録する。実装後にカバレッジが下がった・テストが壊れた場合に比較できる基準を作る。

## 実行手順

1. 関連する Apex テストクラスを特定する:
   ```bash
   Grep pattern: {変更対象クラス名}
   ファイル: force-app/**/*Test*.cls
   ```
2. テストを実行してベースライン状態を記録する:
   ```bash
   sf apex run test --class-names {TestClassName} --target-org {sandbox-alias} --json
   ```
3. 以下を記録する:
   - 全テストメソッド名と PASS / FAIL 状態
   - カバレッジ（変更対象クラスのカバレッジ %）
   - 実行時間（ベースライン）
4. 記録を validation-report.md に保存する（実装後の比較に使う）

## 出力

validation-report.md に追記:

## 変更前テストベースライン

| テストクラス | テストメソッド数 | PASS | FAIL | カバレッジ |
|---|---|---|---|---|
| {TestClassName} | {N} | {N} | 0 | {N}% |

記録日時: {YYYY-MM-DD HH:MM}
