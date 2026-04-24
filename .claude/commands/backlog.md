---
description: "Backlog課題の調査・対応・記録を一気通貫で実施する。専門エージェントを順に起動し、各フェーズ完了後にユーザ確認を取りながら進める。/backlog [課題ID] または /backlog summary で工数サマリーを出力。"
---

# /backlog [課題ID] または [summary]

**モード判定**: 引数が `summary`（大文字・小文字問わず）なら [summary] モードを実行する。それ以外は [課題ID] モードを実行する。

## 概要

保守課題の対応を5つの専門エージェントが分担する。各フェーズはエージェントに完全委譲し、フェーズ間でユーザ確認・xlsx更新を行う。

| フェーズ | エージェント | 主な成果物 |
|---|---|---|
| Phase 0: 開始時刻記録 | orchestrator | `start-time.txt` |
| Phase 1: 調査・理解 | `backlog-investigator` | `investigation.md` |
| Phase 1.5: 対応記録作成 | orchestrator | `{issueID}_対応記録.xlsx` |
| Phase 2: 対応方針の確定 | `backlog-planner` Phase A | `approach-plan.md` |
| Phase 3: 実装方針の確定 | `backlog-planner` Phase B | `implementation-plan.md` |
| Phase 4: 実装 | `backlog-implementer` | 変更ファイル一覧 |
| Phase 5: テスト・検証 | `backlog-tester` | テスト結果レポート |
| Phase 6: リリース・完了 | `backlog-releaser` | 完了報告 |

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
| 日付 | 課題ID | 対応内容 | 見込み（CC） | 見込み（非CC） | 実績（CC） | 削減効果 | 担当 |

### 集計
- 対応課題数 / CC使用合計 / 削減時間合計 / 平均削減率
```

---

## [課題ID] モード — 実行手順

> **絶対ルール**
> - 各フェーズ完了後、次へ進む前にユーザ確認を取る
> - **承認ゲート**: 「次に進む条件」では AskUserQuestion で **[承認 / 修正依頼 / 中止]** の 3 択を提示し、ユーザの明示的な回答を待つ。自由入力での確認は不可。
> - 実装は Phase 4 以降。それ以前に実装コードを書くことは禁止
> - **本番環境（isSandbox=false）への直接デプロイは絶対に行わない**

---

### Phase 0: 開始時刻の記録

```bash
mkdir -p docs/logs/{issueID} && date "+%Y-%m-%d %H:%M:%S" | tee docs/logs/{issueID}/start-time.txt
```

この時刻を `docs/logs/{issueID}/start-time.txt` に保存する。

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

`{xlsx_folder}` = null として Phase 2 へ進む。途中で xlsx を追加したくなった場合は「Phase 1.5 をもう一度実行する」とユーザに伝えればよい。

#### 「作成する」が選ばれた場合

**フォルダパスの確定**

`docs/.backlog_config.yml` を確認する:

- **初回（設定なし）**: 保存先フォルダパスをテキストで入力してもらう（絶対パスで指定。例: `C:/work/backlog_records`）
- **2回目以降**: AskUserQuestion で「{前回のパス}（前回と同じ）」か「別のパスを指定する」を選択

確定したパスを `docs/.backlog_config.yml` の `report_dir` に保存する（絶対パスで指定、例: `C:/work/backlog_records`）:

```yaml
report_dir: "C:/work/backlog_records"
```

`{xlsx_folder}` = `{report_dir}/{issueID}_{件名_sanitized}` として会話の最後まで保持する。  
※ `{件名_sanitized}` は件名の Windows 禁則文字（`/ \ : * ? " < > |`）を `_` に置換した文字列。

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

> **[共通ルール①]** 各フェーズの `timeline` 呼び出しで判断・選択の根拠がある場合は `--reason "{根拠}"` を追加する（例: 排除した案の理由、採用した方針の根拠）。記録の追跡性を高めるため積極的に使用すること。
>
> **[共通ルール②]** xlsx の「対応方針」「実装方針」「テスト結果」「リリース」シートに書き込む場合は `update_records.py cell --sheet "{シート名}" --row {行番号} --col {列番号} --value "{値}"` を使用する。各シートは生成直後は空のため、対応するフェーズで適宜埋めること。

```bash
python scripts/python/backlog-xlsx/update_records.py \
  --folder "{xlsx_folder}" --issue-id "{issueID}" \
  timeline --phase "調査" \
  --content "調査完了: {根本原因または要件の本質を1行で}"
```

> **次に進む条件: ユーザが xlsx 生成と調査レポートを確認した後**
>
> **デプロイ適否判定**: ユーザ確認前に以下「デプロイ適否の判定」セクションを参照し、実装・デプロイをスキップすべきか確認する。スキップ該当の場合は Phase 2 方針欄に明記して Phase 6 へ進む。

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
  --source "ユーザ" \
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
  --source "ユーザ" \
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

エージェントが Before/After を提示したらユーザに確認する。変更ファイルが 5 件を超える場合は、最も重要な変更（ロジック変更・インターフェース変更）を詳細提示し、その他は変更ファイル名と変更理由の一覧で省略する。

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

テスト結果をユーザに報告する。NG項目があれば Phase 4 に戻って実装を修正し、**全テストケースを再度 Phase 5 で実施**してから Phase 6 に進む（部分的な再テストは不可）。

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
開始時刻ファイル: docs/logs/{issueID}/start-time.txt
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

- `git status` で force-app/ 配下に未コミット差分が 30 ファイル以上ある（デプロイで意図しない設定が上書きされるリスク）
- ページレイアウト・プロファイル等、管理画面からの直接編集が SF 推奨のメタデータのみ変更
- コード変更が不要で Salesforce 管理画面の設定変更だけで完結する（Apex/LWC/Flow の追加・変更なし）

→ 該当する場合は Phase 2 の方針欄に「実装不要・管理画面直接操作」と明記し、操作手順をユーザに案内して Phase 6 へスキップする。

---

## 使用例

```
/backlog GF-327     # GF-327 の対応を実施
/backlog summary    # 全課題の工数サマリーを出力
```
