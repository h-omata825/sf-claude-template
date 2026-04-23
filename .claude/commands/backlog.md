---
description: "Backlog課題の調査・対応・記録を一気通貫で実施する。専門エージェントを順に起動し、各フェーズ完了後にユーザ確認を取りながら進める。/backlog [課題ID] または /backlog summary で工数サマリーを出力。"
---

# /backlog [課題ID] または [summary]

## 概要

保守課題の対応を5つの専門エージェントが分担する。各フェーズはエージェントに完全委譲し、フェーズ間でユーザ確認・xlsx更新を行う。

| フェーズ | エージェント | 旧Step相当 |
|---|---|---|
| Phase 0: 開始時刻記録 | orchestrator | Step 0 |
| Phase 1: 調査・理解 | `backlog-investigator` | Step 1 + Step 3 |
| Phase 1.5: 対応記録作成 | orchestrator | Step 2 |
| Phase 2: 対応方針の確定 | `backlog-planner` Phase A | Step 5 |
| Phase 3: 実装方針の確定 | `backlog-planner` Phase B | Step 6 |
| Phase 4: 実装 | `backlog-implementer` | Step 7 |
| Phase 5: テスト・検証 | `backlog-tester` | Step 8 |
| Phase 6: リリース・完了 | `backlog-releaser` | Step 10 + Step 11 + Step 12 |

**中間成果物の保存先**: `docs/logs/{issueID}/`
- `investigation.md` — 調査レポート
- `approach-plan.md` — 対応方針
- `implementation-plan.md` — 実装方針（全判断ポイント確定版）

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
> - 実装は Phase 4 以降。それ以前に実装コードを書くことは禁止
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

エージェントが `investigation.md` を保存したら、内容をユーザに提示する。

> **次に進む条件: ユーザが調査レポートを確認した後**

---

### Phase 1.5: 対応記録ファイルの作成（選択式）

AskUserQuestion で以下を表示する:

**質問**: 「対応記録・エビデンスxlsxを作成しますか？」

**選択肢**:
- label: "作成する（推奨）" description: "対応記録.xlsx と エビデンス.xlsx を作成して記録を残す"
- label: "作成しない" description: "ファイルなしで調査・対応のみ行う"

#### 「作成しない」が選ばれた場合

`{xlsx_folder}` = null として Phase 2 へ進む。

#### 「作成する」が選ばれた場合

**フォルダパスの確定**

`docs/.backlog_config.yml` を確認する:

- **初回（設定なし）**: 保存先フォルダパスをテキストで入力してもらう
- **2回目以降**: AskUserQuestion で「{前回のパス}（前回と同じ）」か「別のパスを指定する」を選択

確定したパスを `docs/.backlog_config.yml` の `report_dir` に保存する。  
`{xlsx_folder}` = `{report_dir}/{issueID}_{件名}` として会話の最後まで保持する。

**xlsx の生成**

`investigation.md` から件名・種別・優先度・期限・要約を読み取って実行する:

```bash
python scripts/python/backlog-xlsx/create_records.py \
  --folder "{xlsx_folder}" \
  --issue-id "{issueID}" \
  --title "{件名}" \
  --type "{バグ/追加要望/その他}" \
  --priority "{優先度}" \
  --deadline "{期限}" \
  --summary "{要約}"

python scripts/python/backlog-xlsx/create_evidence.py \
  "{xlsx_folder}" "{issueID}"
```

**xlsx 更新（調査・影響範囲）**

```bash
python scripts/python/backlog-xlsx/update_records.py \
  --folder "{xlsx_folder}" --issue-id "{issueID}" \
  timeline --phase "調査" \
  --content "調査完了: {根本原因または要件の本質を1行で}"
```

> **次に進む条件: ユーザが確認した後**

---

### Phase 2: 対応方針の確定（backlog-planner Phase A）

`backlog-planner` エージェントを起動する（Phase A: 対応方針）:

```
モード: 対応方針（Phase A）
調査レポート: docs/logs/{issueID}/investigation.md
出力先: docs/logs/{issueID}/approach-plan.md
```

エージェントが `approach-plan.md` を保存したら提示する。  
ユーザが採用方針を確定するまで Phase 3 に進まない。

**xlsx 更新（対応方針）**（`{xlsx_folder}` が設定されている場合のみ）

```bash
python scripts/python/backlog-xlsx/update_records.py \
  --folder "{xlsx_folder}" --issue-id "{issueID}" \
  timeline --phase "方針策定" \
  --content "対応方針確定: {採用した案名と根拠を1行で}"
```

工数見込みを `docs/logs/effort-log.md` に追記する（CC使用 Xh / CC未使用 Xh）。

> **次に進む条件: ユーザが対応方針を承認した後**

---

### Phase 3: 実装方針の確定（backlog-planner Phase B）

`backlog-planner` エージェントを起動する（Phase B: 実装方針）:

```
モード: 実装方針（Phase B）
採用方針: {承認された案名}
調査レポート: docs/logs/{issueID}/investigation.md
出力先: docs/logs/{issueID}/implementation-plan.md
```

エージェントが `implementation-plan.md` を保存したら提示する。  
全判断ポイントが確定するまで Phase 4 に進まない。

**xlsx 更新（対応方針詳細）**（`{xlsx_folder}` が設定されている場合のみ）

```bash
python scripts/python/backlog-xlsx/update_records.py \
  --folder "{xlsx_folder}" --issue-id "{issueID}" \
  timeline --phase "実装方針確定" \
  --content "全判断ポイント確定: {主要な判断を1行で}"
```

> **次に進む条件: 全判断ポイントをユーザが確認・確定した後**

---

### Phase 4: 実装（backlog-implementer）

`backlog-implementer` エージェントを起動する:

```
実装計画: docs/logs/{issueID}/implementation-plan.md
調査レポート: docs/logs/{issueID}/investigation.md
```

エージェントが Before/After を提示したらユーザに確認する。

**xlsx 更新（対応内容）**（`{xlsx_folder}` が設定されている場合のみ）

```bash
python scripts/python/backlog-xlsx/update_records.py \
  --folder "{xlsx_folder}" --issue-id "{issueID}" \
  timeline --phase "実装" \
  --content "実装完了: {変更ファイル数}ファイル変更 / {主な変更点を1行で}"
```

> **次に進む条件: ユーザが実装内容を確認した後**

---

### Phase 5: テスト・検証（backlog-tester）

`backlog-tester` エージェントを起動する:

```
調査レポート: docs/logs/{issueID}/investigation.md
実装計画: docs/logs/{issueID}/implementation-plan.md
```

テスト結果をユーザに報告する。NG項目があれば Phase 4 に戻る。

**xlsx 更新（テスト・検証記録）**（`{xlsx_folder}` が設定されている場合のみ）

```bash
python scripts/python/backlog-xlsx/update_records.py \
  --folder "{xlsx_folder}" --issue-id "{issueID}" \
  timeline --phase "テスト" \
  --content "テスト完了: {PASS/FAIL} / {テスト件数}件実施"
```

> **次に進む条件: 全テスト PASS をユーザが確認した後**

---

### Phase 6: リリース・完了（backlog-releaser）

`backlog-releaser` エージェントを起動する:

```
実装計画: docs/logs/{issueID}/implementation-plan.md
xlsx_folder: {xlsx_folder}（設定されている場合）
開始時刻: {Phase 0 で記録した時刻}
```

**xlsx 更新（リリース・サマリー）**（`{xlsx_folder}` が設定されている場合のみ）

```bash
python scripts/python/backlog-xlsx/update_records.py \
  --folder "{xlsx_folder}" --issue-id "{issueID}" \
  timeline --phase "リリース" \
  --content "リリース準備完了 / 実績工数: {実績}h（削減効果: {削減率}%）"
```

完了報告を行う。

---

## デプロイ適否の判定（Phase 1 終了時に適用）

以下の場合、実装・デプロイ（Phase 4〜5）をスキップして管理画面直接操作を案内する:

- 本番とリポジトリのメタデータが大きく乖離しており、デプロイで意図的な設定が上書きされるリスクがある
- ページレイアウト・プロファイル等「管理画面から直接編集する方が安全」なメタデータのみ変更
- コード変更が不要で Salesforce 管理画面の設定変更だけで完結する

→ 該当する場合は Phase 2 の方針欄に「実装不要・管理画面直接操作」と明記し、操作手順をユーザに案内して Phase 6 へスキップする。

---

## 使用例

```
/backlog GF-327     # GF-327 の対応を実施
/backlog summary    # 全課題の工数サマリーを出力
```
