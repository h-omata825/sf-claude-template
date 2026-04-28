# option-anti-pattern-check

## 何をするか

実装計画に Apex アンチパターンが含まれていないか確認する。代表的な問題（God Class / 巨大トランザクション / SOQL in loop / hardcoded ID）を検出する。

## 実行手順

1. 実装計画（implementation-plan.md）の Apex 実装部分を確認する
2. 以下のアンチパターンを順番に確認する:

   **SOQL in loop**:
   - ループ内で SOQL を実行する設計になっていないか
   - 対策: ループ外で事前にデータを一括取得して Map で引く

   **Hardcoded ID / 環境依存値**:
   - レコード ID・プロファイル ID・権限セット ID をハードコードしていないか
   - 対策: カスタム設定・Custom Metadata / SOQL での動的取得

   **God Class**:
   - 既存の大きなクラスにさらにロジックを追加する設計でないか
   - 対策: 責務を分離して専用クラスを新設

   **巨大トランザクション**:
   - 1 トランザクションに複数の DML + SOQL + Callout が混在していないか
   - ガバナ制限（SOQL 100 件 / DML 150 件 / CPU 時間 10 秒）を超えるリスク

   **Governor Limit 無考慮**:
   - 大量データ時のガバナ制限超過リスクを考慮しているか

   **Null チェック欠如**:
   - 外部から受け取る値・クエリ結果の Null チェックが実装計画に含まれているか

3. 発見したアンチパターンを implementation-plan.md に記録して修正案を提示する

## 出力

implementation-plan.md に追記:

## アンチパターン検出結果

| アンチパターン | 検出 | 修正案 |
|---|---|---|
| SOQL in loop | 検出なし / 検出（{箇所}） | {修正方法} |
| Hardcoded ID | 検出なし / 検出（{箇所}） | Custom Metadata に移行 |
| God Class | 検出なし / 検出 | 責務分離・新クラス化 |
| 巨大トランザクション | 検出なし / リスクあり | 分割・非同期化 |
