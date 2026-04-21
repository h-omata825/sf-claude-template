---
description: "Backlog課題の調査・対応・記録を一気通貫で実施する。専門エージェントを順に起動し、各フェーズ完了後にユーザ確認を取りながら進める。/backlog [課題ID] または /backlog summary で工数サマリーを出力。"
---

# /backlog [課題ID] または [summary]

## 概要

保守課題の対応を5つの専門エージェントが分担する。各フェーズはエージェントに完全委譲し、フェーズ間でユーザ確認を取る。

| フェーズ | エージェント | 役割 |
|---|---|---|
| 調査・理解 | `backlog-investigator` | 課題読解・コード分析・類似実装特定・業務要件抽出 |
| 対応方針 | `backlog-planner`（Phase A） | 全対応案の提示と方針確定 |
| 実装方針 | `backlog-planner`（Phase B） | 全実装判断ポイントの提示と確定 |
| 実装 | `backlog-implementer` | 承認済み計画の忠実な実装 |
| テスト | `backlog-tester` | 機能テスト・実装レビュー |
| リリース・完了 | `backlog-releaser` | リリース準備・ドキュメント・工数記録 |

**成果物保存先**: `docs/logs/{issueID}/`
- `investigation.md` — 調査レポート
- `approach-plan.md` — 対応方針
- `implementation-plan.md` — 実装方針

---

## [summary] モード

`docs/logs/effort-log.md` を読み込み、以下の形式でサマリーを出力する:

```
## 工数サマリー

### 全課題一覧
| 課題ID | 件名 | 種別 | 見込み（CC） | 実績（CC） | 削減効果 | 対応日 |

### 集計
- 対応課題数 / CC使用合計 / 削減時間合計 / 平均削減率
```

---

## [課題ID] モード — 実行手順

> **絶対ルール**
> - 各フェーズ完了後、次へ進む前にユーザ確認を取る
> - 実装はフェーズ4以降。それ以前に実装コードを書くことは禁止
> - **本番環境（isSandbox=false）への直接デプロイは絶対に行わない**

---

### Phase 0: 開始時刻の記録

```bash
date "+%Y-%m-%d %H:%M:%S"
```

この時刻を会話の最後まで保持する。

---

### Phase 1: 調査（backlog-investigator）

`backlog-investigator` エージェントを起動する:

```
課題ID: {issueID}
プロジェクトルート: {カレントディレクトリ}
出力先: docs/logs/{issueID}/investigation.md
```

エージェントが `investigation.md` を保存したら内容をユーザに提示する。

> **次に進む条件: ユーザが調査レポートを確認した後**

---

### Phase 2: 対応方針の確定（backlog-planner Phase A）

`backlog-planner` エージェントを起動する（Phase A）:

```
モード: 対応方針（Phase A）
調査レポート: docs/logs/{issueID}/investigation.md
出力先: docs/logs/{issueID}/approach-plan.md
```

エージェントが `approach-plan.md` を保存したら提示する。ユーザが方針を確定するまで次に進まない。

> **次に進む条件: ユーザが対応方針（案X）を承認した後**

---

### Phase 3: 実装方針の確定（backlog-planner Phase B）

`backlog-planner` エージェントを起動する（Phase B）:

```
モード: 実装方針（Phase B）
採用方針: {承認された案名}
調査レポート: docs/logs/{issueID}/investigation.md
出力先: docs/logs/{issueID}/implementation-plan.md
```

エージェントが `implementation-plan.md` を保存したら提示する。全判断ポイントが確定するまで次に進まない。

> **次に進む条件: 全判断ポイントをユーザが確認・確定した後**

---

### Phase 4: 実装（backlog-implementer）

`backlog-implementer` エージェントを起動する:

```
実装計画: docs/logs/{issueID}/implementation-plan.md
調査レポート: docs/logs/{issueID}/investigation.md
```

エージェントが Before/After を提示したらユーザに確認する。

> **次に進む条件: ユーザが実装内容を確認した後**

---

### Phase 5: テスト・検証（backlog-tester）

`backlog-tester` エージェントを起動する:

```
調査レポート: docs/logs/{issueID}/investigation.md
```

テスト結果をユーザに報告する。NG項目があれば Phase 4 に戻る。

> **次に進む条件: 全テスト PASS をユーザが確認した後**

---

### Phase 6: リリース・完了（backlog-releaser）

`backlog-releaser` エージェントを起動する。完了報告を行う。

---

## デプロイ適否の判定（Phase 1 終了時に適用）

以下の場合、実装・デプロイ（Phase 4〜5）をスキップして管理画面直接操作を案内する:

- 本番とリポジトリのメタデータが大きく乖離しており、デプロイで意図的な設定が上書きされるリスクがある
- ページレイアウト・プロファイル等「管理画面から直接編集する方が安全」なメタデータのみ変更
- コード変更が不要で Salesforce 管理画面の設定変更だけで完結する

---

## 対応記録 xlsx（省略可）

フォルダ入力後に以下で生成する:

```bash
python scripts/python/backlog-xlsx/create_records.py \
  --folder "{フォルダパス}" --issue-id "{issueID}" \
  --title "{件名}" --type "{種別}" --priority "{優先度}" \
  --deadline "{期限}" --summary "{要約}"

python scripts/python/backlog-xlsx/create_evidence.py "{フォルダパス}" "{issueID}"
```

xlsx 更新方法:
```bash
python scripts/python/backlog-xlsx/update_records.py \
  --folder "{フォルダパス}" --issue-id "{issueID}" \
  timeline --phase "調査" --content "〇〇を調査: 原因は△△"
```

---

## 使用例

```
/backlog GF-327     # GF-327 の対応を実施
/backlog summary    # 全課題の工数サマリーを出力
```
