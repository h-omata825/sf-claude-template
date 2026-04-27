---
description: "Backlog課題の調査・対応・記録を一気通貫で実施する。専門エージェントを順に起動し、各フェーズ完了後にユーザ確認を取りながら進める。/backlog [課題ID] または /backlog summary で工数サマリーを出力。"
---

# /backlog [課題ID] または [summary]

**モード判定**: 引数が `summary`（大文字・小文字問わず）なら [summary] モードを実行する。それ以外は [課題ID] モードを実行する。

## 概要

保守課題の対応を5つの専門エージェントが分担する。各フェーズはエージェントに完全委譲し、フェーズ間でユーザ確認・xlsx更新を行う。

| フェーズ | エージェント | 主な成果物 |
|---|---|---|
| Phase 0: 作業フォルダ作成 | （本コマンド直接実行） | `docs/logs/{issueID}/` |
| Phase 1: 調査・理解 | `backlog-investigator` | `investigation.md` |
| Phase 1.5: 対応記録作成 | （本コマンド直接実行） | `{issueID}_対応記録.xlsx` |
| Phase 2: 対応方針の確定 | `backlog-planner` Phase A | `approach-plan.md` |
| Phase 3: 実装方針の確定 | `backlog-planner` Phase B | `implementation-plan.md` |
| Phase 3.5: 実装前検証 | `backlog-validator` | `validation-report.md` |
| Phase 4: 実装 | `backlog-implementer`（内部: `sf-context-loader`） | 変更ファイル一覧 |
| Phase 5: テスト・検証 | `backlog-tester`（内部: `sf-context-loader`） | テスト結果レポート |
| Phase 6: リリース・完了 | `backlog-releaser`（内部: `sf-context-loader`） | 完了報告 |

**各エージェントの内部構造**: `backlog-implementer` / `backlog-tester` / `backlog-releaser` / `backlog-validator` は Phase 0 で `sf-context-loader` を呼び出して関連 docs を選択的にロードする。`backlog-investigator` / `backlog-planner` は docs/ を直接全件読みするため Phase 0 を持たない。

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
| 日付 | 課題ID | 対応内容 | 見込み工数 | 担当 |

### 集計
- 対応課題数 / 見込み工数合計
```

---

## [課題ID] モード — 実行手順

> **絶対ルール**
> - 各フェーズ完了後、次へ進む前にユーザ確認を取る
> - **承認ゲート**: 「次に進む条件」では AskUserQuestion で **[承認 / 修正依頼 / 中止]** の 3 択を提示し、ユーザの明示的な回答を待つ。自由入力での確認は不可。
> - **議論モード**: 各 Phase 末の承認ゲート提示前に、エージェントは以下を必ず行う:
>   1. 提示内容の 3〜5 行サマリー（要点を簡潔に）
>   2. 「特に確認したい点」を 1〜3 個挙げる（懸念点・前提の弱い箇所・複数解釈ありうる点）
>   3. AskUserQuestion で **[議論する / 承認に進む]** を提示
>   4. 「議論する」が選ばれたら、エージェントが事前に用意した深掘り選択肢で AskUserQuestion を続ける（例: 「Q1 の回答は A/B/C のどれか」「副作用 X を許容するか抑制するか」）
>   5. 議論完了後、改めて承認ゲート **[承認 / 修正依頼 / 中止]** を提示
> - 実装は Phase 4 以降。それ以前に実装コードを書くことは禁止
> - **xlsx 更新の共通ルール**: Phase 1.5 で定義される共通ルール①（timeline 呼び出しに `--reason "{根拠}"` を追加）と共通ルール②（xlsx シート書き込みは `update_records.py cell` を使用）は Phase 2 以降の全 timeline 更新で適用すること（詳細は「Phase 1.5: 対応記録ファイルの作成」セクションの共通ルール定義を参照）
> - **本番環境（isSandbox=false）への直接デプロイは絶対に行わない**

---

### Phase 0: 作業フォルダの作成

```bash
mkdir -p docs/logs/{issueID}
```

`docs/logs/{issueID}/investigation.md` が既に存在する場合は続きから再開するか確認する。AskUserQuestion で **[Phase 1 から再調査 / 途中フェーズから再開 / 中止]** を提示してユーザに確認する。

**「途中フェーズから再開」が選ばれた場合**: `docs/logs/{issueID}/` 配下の既存成果物の有無に応じて、AskUserQuestion で再開フェーズを提示する:

- `validation-report.md` 存在 → **[Phase 4（実装）から / Phase 3.5（実装前検証）から / 中止]**
- `implementation-plan.md` 存在（validation-report.md なし） → **[Phase 3.5（実装前検証）から / Phase 3（実装方針確定）から / 中止]**
- `approach-plan.md` 存在（implementation-plan.md なし） → **[Phase 3（実装方針確定）から / Phase 2（対応方針確定）から / 中止]**
- `investigation.md` のみ存在 → **[Phase 2（対応方針確定）から / Phase 1.5（対応記録作成）から / 中止]**

選択されたフェーズの該当節へ進む。前フェーズの成果物は再生成せず保持する。

---

### Phase 1: 調査（backlog-investigator）

`backlog-investigator` エージェントを起動する:

```
課題ID: {issueID}
プロジェクトルート: {カレントディレクトリ}
出力先: docs/logs/{issueID}/investigation.md
```

エージェントが `investigation.md` を保存したら、内容をユーザに提示する。

**実装前エビデンスの取得依頼**（調査レポート提示直後に案内する）

ユーザに以下を案内する:
- **バグの場合**: 再現手順を実機で実施し、画面スクリーンショット・コンソールログ・対象レコード値を取得。xlsx エビデンスシートの「実装前エビデンス」欄に貼付、または `docs/logs/{issueID}/evidence/before/` 配下に保存
- **追加要望の場合**: 変更前の現状画面・データの状態をスクリーンショット保存（変更後との比較用）
- **その他の場合**: 変更前の現状（対象画面・データ・処理結果等）を記録しておくことを推奨する（スクリーンショットまたはファイルで `docs/logs/{issueID}/evidence/before/` 配下に保存）
- **Playwright が利用可能な場合**（`.mcp.json` に playwright MCP サーバー設定があり、対象画面が Sandbox 認証済みブラウザで開ける場合）: エージェント側でも対象画面のスクリーンショットを自動取得し `docs/logs/{issueID}/evidence/before/auto_{連番}_{説明}.png` に保存する（精度が低い場合はユーザ案内のみ）

エビデンスは Phase 3.5（実装前検証）と Phase 5（クロステスト）で参照される。

> **次に進む条件**: ユーザが調査レポートとエビデンス取得案内を確認した後 — 議論モードを挟んでから AskUserQuestion で **[承認 / 修正依頼 / 中止]** を提示する
>
> **議論モードで挙げる懸念点の例**: 「類似実装 X の実装パターンと異なる場合の整合性」「業務要件 Q1 への仮説が正しいか」

---

### Phase 1.5: 対応記録ファイルの作成（選択式）

AskUserQuestion で以下を表示する:

**質問**: 「対応記録・エビデンスxlsxを作成しますか？」

**選択肢**:
- label: "作成する" description: "対応記録.xlsx と エビデンス.xlsx を作成して記録を残す（推奨）"
- label: "作成しない" description: "ファイルなしで調査・対応のみ行う"

#### 「作成しない」が選ばれた場合

`{xlsx_folder}` = null として Phase 2 へ進む。途中で xlsx を追加したくなった場合は「Phase 1.5 をもう一度実行する」とユーザに伝えればよい。

#### 「作成する」が選ばれた場合

**フォルダパスの確定**

`docs/.backlog_config.yml` を確認する（出力が空の場合は初回として扱う）:

```bash
python -c "import yaml,pathlib; p=pathlib.Path('docs/.backlog_config.yml'); d=yaml.safe_load(p.read_text(encoding='utf-8')) if p.exists() else {}; print(d.get('report_dir',''))"
```

- **初回（出力が空）**: 保存先フォルダパスをテキストで入力してもらう（絶対パスで指定。例: `C:/work/backlog_records`）
- **2回目以降（出力に前回パスあり）**: AskUserQuestion で「{前回のパス}（前回と同じ）」か「別のパスを指定する」を選択。「別のパスを指定する」が選ばれた場合は、初回と同じく保存先フォルダパスを絶対パスでテキスト入力してもらう

確定したパスを `docs/.backlog_config.yml` の `report_dir` に保存する:

```bash
python -c "import yaml,pathlib; pathlib.Path('docs/.backlog_config.yml').write_text(yaml.dump({'report_dir': '{確定したパス}'}), encoding='utf-8')"
```

`{件名}` から Windows 禁則文字を除去した `{件名_sanitized}` を生成する（出力値を変数として保持すること）:

```bash
python -c "import re,sys; print(re.sub(r'[/\\\\:*?\"<>|]', '_', sys.argv[1]))" "{件名}"
```

`{xlsx_folder}` = `{report_dir}/{issueID}_{件名_sanitized}` として会話の最後まで保持する。

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

スクリプトが失敗した場合（エラー出力あり / 終了コード 非0）:
- ユーザーに失敗内容を報告し、AskUserQuestion で **[エクセルなしで続行 / 中止]** を提示する
- 「エクセルなしで続行」が選ばれた場合: `{xlsx_folder}` を null に設定して Phase 2 へ進む

**xlsx 更新（調査・影響範囲）**

> **[共通ルール①]** 各フェーズの `timeline` 呼び出しで判断・選択の根拠がある場合は `--reason "{根拠}"` を追加する（例: 排除した案の理由、採用した方針の根拠）。記録の追跡性を高めるため積極的に使用すること。
>
> **[共通ルール②]** xlsx の「対応方針」「実装方針」「テスト結果」「リリース」シートに書き込む場合は `update_records.py cell --sheet "{シート名}" --row {行番号} --col {列番号} --value "{値}"` を使用する。各シートは生成直後は空のため、各フェーズの xlsx 更新ブロックで埋めること（Phase 2～6 の各 xlsx 更新コマンドを参照）。

```bash
python scripts/python/backlog-xlsx/update_records.py \
  --folder "{xlsx_folder}" --issue-id "{issueID}" \
  timeline --phase "調査" \
  --content "調査完了: {根本原因または要件の本質を1行で}"
```

> **次に進む条件**: ユーザが xlsx 生成と調査レポートを確認した後 — AskUserQuestion で **[承認 / 修正依頼 / 中止]** を提示する
>
> **デプロイ適否判定**: ユーザ確認前に以下「デプロイ適否の判定」セクションを参照し、実装・デプロイをスキップすべきか確認する。スキップ該当の場合は Phase 2 方針欄に明記して Phase 6 へ進む。

---

### Phase 2: 対応方針の確定（backlog-planner Phase A）

> **xlsx 共通規則**: Phase 2 以降の全 xlsx 更新ブロックは `{xlsx_folder}` が null（Phase 1.5 で「作成しない」を選択）の場合スキップする。

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

工数見込みを `docs/logs/effort-log.md` に追記する（以下の形式で最終行の後へ追記する）:

```
| {YYYY-MM-DD} | {issueID} | {対応内容を1行で} | {Xh} | {担当者名} |
```

> **次に進む条件**: ユーザが対応方針を承認した後 — 議論モードを挟んでから AskUserQuestion で **[承認 / 修正依頼 / 中止]** を提示する
>
> **議論モードで挙げる懸念点の例**: 「業務要件 Q の回答が方針の前提と合っているか」「推奨案と比較した際の非採用案のリスク許容判断」

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

> **次に進む条件**: 全判断ポイントをユーザが確認・確定した後 — 議論モードを挟んでから AskUserQuestion で **[承認 / 修正依頼 / 中止]** を提示する
>
> **議論モードで挙げる懸念点の例**: 「類似実装と異なるパターンを採用した判断ポイントの整合性」「SOQL の LIMIT・権限制御が全ユーザ種別で正しいか」

---

### Phase 3.5: 実装前検証（backlog-validator）

`backlog-validator` エージェントを起動する:

```
実装計画: docs/logs/{issueID}/implementation-plan.md
調査レポート: docs/logs/{issueID}/investigation.md
```

エージェントが `validation-report.md` を保存したら内容をユーザに提示する。Phase 3 への戻りが提案された場合は Phase 3 に戻って実装方針を修正してから Phase 3.5 を再実施する。

**xlsx 更新（実装前検証）**（`{xlsx_folder}` が設定されている場合のみ）

```bash
python scripts/python/backlog-xlsx/update_records.py \
  --folder "{xlsx_folder}" --issue-id "{issueID}" \
  timeline --phase "実装前検証" \
  --content "実装前検証完了: {ドライラン/テスト/影響範囲/クロスレビュー/エビデンスの結果サマリーを1行で}"
```

> **次に進む条件**: 全検証項目 OK をユーザが確認した後 — 議論モードを挟んでから AskUserQuestion で **[承認（Phase 4 へ） / Phase 3 に戻る / 中止]** を提示する
>
> **議論モードで挙げる懸念点の例**: 「新規発見した影響箇所への対処方針」「エビデンスが取れていない項目の扱い」

---

### Phase 4: 実装（backlog-implementer）

`backlog-implementer` エージェントを起動する:

```
実装計画: docs/logs/{issueID}/implementation-plan.md
調査レポート: docs/logs/{issueID}/investigation.md
```

エージェントが Before/After を提示したらユーザに確認する。変更ファイルが 5 件を超える場合は以下の基準で提示を分ける:
- **詳細提示**: ロジック変更・public インターフェース変更・Apex/LWC/Flow のコード変更
- **一覧省略可**: 設定ファイル・メタデータ（field-meta.xml / layout-meta.xml 等）・テストクラス以外の補助ファイル

**xlsx 更新（対応内容）**（`{xlsx_folder}` が設定されている場合のみ）

```bash
python scripts/python/backlog-xlsx/update_records.py \
  --folder "{xlsx_folder}" --issue-id "{issueID}" \
  timeline --phase "実装" \
  --content "実装完了: {変更ファイル数}ファイル変更 / {主な変更点を1行で}"
```

> **次に進む条件**: ユーザが実装内容を確認した後 — 議論モードを挟んでから AskUserQuestion で **[承認 / 修正依頼 / 中止]** を提示する
>
> **議論モードで挙げる懸念点の例**: 「実装中に発見した計画との不整合の影響評価」「implementation-plan.md への改版履歴追記が必要なら内容の確認」

---

### Phase 5: テスト・検証（backlog-tester）

`backlog-tester` エージェントを起動する:

```
調査レポート: docs/logs/{issueID}/investigation.md
実装計画: docs/logs/{issueID}/implementation-plan.md
```

テスト結果をユーザに報告する。NG 項目があれば以下の戻り先を判断してから戻る:

| NG の原因 | 戻り先 |
|---|---|
| 実装ミス・コードのバグ | Phase 4（実装修正） |
| 実装方針レベルの判断ミス | Phase 3（実装方針の再確認） |
| 対応方針レベルの設計ミス | Phase 2（対応方針の見直し） |
| 判断できない・複合原因 | ユーザーに戻り先を確認（AskUserQuestion で **[Phase 4 / Phase 3 / Phase 2 / 中止]**） |

戻って修正した後は **全テストケースを再度 Phase 5 で実施**してから Phase 6 に進む（部分的な再テストは不可）。

**xlsx 更新（テスト・検証記録）**（`{xlsx_folder}` が設定されている場合のみ）

```bash
python scripts/python/backlog-xlsx/update_records.py \
  --folder "{xlsx_folder}" --issue-id "{issueID}" \
  timeline --phase "テスト" \
  --content "テスト完了: {PASS/FAIL} / {テスト件数}件実施"
```

> **次に進む条件**: 全テスト PASS かつユーザ確認サインがあった後 — 議論モードを挟んでから AskUserQuestion で **[承認 / 修正依頼 / 中止]** を提示する
>
> **議論モードで挙げる懸念点の例**: 「ユーザ合同確認が取れていないシナリオの扱い」「Before/After エビデンスが対になっているか」

---

### Phase 6: リリース・完了（backlog-releaser）

`backlog-releaser` エージェントを起動する:

```
実装計画: docs/logs/{issueID}/implementation-plan.md
xlsx_folder: {xlsx_folder}（設定されている場合）
```

**xlsx 更新（リリース・サマリー）**（`{xlsx_folder}` が設定されている場合のみ）

```bash
python scripts/python/backlog-xlsx/update_records.py \
  --folder "{xlsx_folder}" --issue-id "{issueID}" \
  timeline --phase "リリース" \
  --content "リリース準備完了"
```

完了報告を行う。

---

## デプロイ適否の判定（Phase 1 終了時に適用）

以下の場合、実装・デプロイ（Phase 4〜5）をスキップして管理画面直接操作を案内する:

- `git status` で force-app/ 配下に未コミット差分が 30 ファイル以上ある（デプロイで意図しない設定が上書きされるリスク）
- ページレイアウト等、コード変更なしで管理画面設定変更のみで完結する（プロファイル・権限セットはメタデータ管理が SF 推奨のため、緊急対応を除き本判定の対象外とし、後でメタデータ取り込みを推奨）
- コード変更が不要で Salesforce 管理画面の設定変更だけで完結する（Apex/LWC/Flow の追加・変更なし）

→ 該当する場合は Phase 2 の方針欄に「実装不要・管理画面直接操作」と明記し、操作手順をユーザに案内して Phase 6 へスキップする。

---

## 使用例

```
/backlog GF-327     # GF-327 の対応を実施
/backlog summary    # 全課題の工数サマリーを出力
```
