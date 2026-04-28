# option-reverse-grep

## 何をするか

変更対象の API 名・メソッド名・フィールド名を `force-app/` 全体から Grep で逆参照する。

## 実行手順

1. 変更対象の名前リストを作成する（API 名・メソッド名・フィールド名）
2. 各名前について `force-app/` 全体を Grep で検索する:
   - Apex (`*.cls`, `*.trigger`)
   - LWC (`*.js`, `*.html`)
   - Aura (`*.cmp`, `*.js`)
   - VisualForce (`*.page`)
   - Flow (`*.flow-meta.xml`)
   - 入力規則 (`*.validationRule-meta.xml`)
   - 承認プロセス (`*.approvalProcess-meta.xml`)
   - 割り当てルール (`*.assignmentRules-meta.xml`)
3. ヒットした各箇所について影響を判定する:
   - 影響あり → investigation.md「影響範囲」に追記
   - 影響なし → スキップ理由を簡潔に記録

## 出力

investigation.md「影響範囲」セクションに追記:

| ヒットファイル | 行 | 影響判定 | 対応要否 |
|---|---|---|---|
| ... | ... | ... | ... |
