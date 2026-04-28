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
> - 各フェーズ完了後、次へ進む前にユーザの明示的な許可を必ず取る（黙って次フェーズへ進まない）
> - **AskUserQuestion は使わない**。フェーズ承認・選択肢提示はすべてテキスト会話で行う
> - **フェーズ末の進め方**:
>   1. 成果物の 3〜5 行サマリーをテキストで提示
>   2. 「特に確認したい点」を 1〜3 個テキストで挙げる（懸念点・前提の弱い箇所・複数解釈ありうる点）
>   3. ユーザの自由テキスト応答を待つ（質問・修正依頼・承認 何でも可）
>   4. 議論が落ち着いたら「Phase N に進んでよろしいですか？」とテキストで明示確認
>   5. ユーザの承認テキスト（「OK」「進んで」等）を確認してから次フェーズへ進む
> - 実装は Phase 4 以降。それ以前に実装コードを書くことは禁止
> - **xlsx 更新の共通ルール**: Phase 1.5 で定義される共通ルール①（timeline 呼び出しに `--reason "{根拠}"` を追加）と共通ルール②（xlsx シート書き込みは `update_records.py cell` を使用）は Phase 2 以降の全 timeline 更新で適用すること（詳細は「Phase 1.5: 対応記録ファイルの作成」セクションの共通ルール定義を参照）
> - **本番環境（isSandbox=false）への直接デプロイは絶対に行わない**
> - **種別変数 `{issue_type}` の管理**: Phase 1 完了時点で `investigation.md` の「種別」欄から `{issue_type}` = `バグ` / `追加要望` / `その他` を確定し、会話の最後まで保持する。Phase 1.7（再現確認）・Phase 2（デフォルトスタンス）・Phase 5（テスト観点）・Phase 6（お客様確認必須度）の分岐に使用する

---

### Phase 0: 作業フォルダの作成

**接続組織の確認**

```bash
sf config get target-org
```

```bash
sf org display --json
```

`isSandbox`・`Username`・`alias` を読み取り、以下をテキストで提示する:

```
現在の接続組織:
  alias: {alias名}
  種別: Sandbox / 本番
  Username: {user@example.com}

この組織に対して課題対応を進めてよろしいですか？
（Sandbox: 再現確認・テストにこの組織を使用します）
（本番: 参照のみ可能。データ確認の SELECT 文は都度許可を取ります）
別の組織に切り替えたい場合: sf config set target-org <alias>
```

ユーザーが確認の返答をするまで次に進まない。

```bash
mkdir -p docs/logs/{issueID}
```

`docs/logs/{issueID}/investigation.md` が既に存在する場合は続きから再開するか確認する。「Phase 1 から再調査 / 途中フェーズから再開 / 中止 のどれにしますか？」とテキストで質問する。

**「途中フェーズから再開」が選ばれた場合**: `docs/logs/{issueID}/` 配下の既存成果物の有無に応じて再開可能フェーズをテキストで列挙して選択を促す:

- `validation-report.md` 存在 → 「Phase 4（実装）から / Phase 3.5（実装前検証）から / 中止 のどれにしますか？」
- `implementation-plan.md` 存在（validation-report.md なし） → 「Phase 3.5（実装前検証）から / Phase 3（実装方針確定）から / 中止 のどれにしますか？」
- `approach-plan.md` 存在（implementation-plan.md なし） → 「Phase 3（実装方針確定）から / Phase 2（対応方針確定）から / 中止 のどれにしますか？」
- `investigation.md` のみ存在 → 「Phase 1.7（Sandbox 再現確認）から（バグのみ）/ Phase 2（対応方針確定）から / Phase 1.5（対応記録作成）から / 中止 のどれにしますか？」（バグ以外は Phase 1.7 を提示しない）

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

> **次に進む条件**: ユーザが調査レポートを確認した後 — 成果物サマリーと特に確認したい点をテキストで提示し、やり取りを経て「Phase 1.5 に進んでよろしいですか？」とテキストで確認する
>
> **特に確認したい点の例**: 「類似実装 X の実装パターンと異なる場合の整合性」「業務要件 Q1 への仮説が正しいか」

---

### Phase 1.5: 対応記録ファイルの作成（選択式）

AskUserQuestion で「作成する（推奨）」か「作成しない」を選択してもらう。

> **[共通ルール①]** 各フェーズの `timeline` 呼び出しで判断・選択の根拠がある場合は `--reason "{根拠}"` を追加する（記録の追跡性を高めるため積極的に使用すること）。
>
> **[共通ルール②]** xlsx のシートに書き込む場合は `update_records.py cell --sheet "{シート名}" --row {行番号} --col {列番号} --value "{値}"` を使用する。各シートは生成直後は空のため、各フェーズの xlsx 更新ブロックで埋めること（Phase 2～6 の各 xlsx 更新コマンドを参照）。

> 実行手順（フォルダパス確定・xlsx 生成・エビデンス取得・xlsx 更新）:
> [.claude/templates/backlog/xlsx-setup.md](../templates/backlog/xlsx-setup.md)

---

### Phase 1.7: Sandbox 再現確認（バグのみ）

`{issue_type}` が `バグ` 以外（追加要望 / その他）の場合は本 Phase をスキップして Phase 2 へ。

investigation.md の「再現条件」を Sandbox 環境で実機実行する:

1. **Sandbox 確認**: `sf org display --target-org <alias> --json` で `isSandbox=true` を確認。本番接続が確認された場合は中断してユーザに Sandbox alias を質問
2. **再現手順の実行**:
   - Playwright MCP が利用可能 → 自動実行＋スクリーンショットを `docs/logs/{issueID}/evidence/before/repro/auto_{連番}_{説明}.png` に保存
   - Playwright 不可 → ユーザに再現手順を提示し「同じ事象が出たか」をテキスト確認してもらう
3. **再現エビデンス取得**: 画面スクリーンショット・コンソールログ・対象レコード値を `docs/logs/{issueID}/evidence/before/repro/` に保存
4. **ユーザ確認**: 「Backlog 課題と同じ事象が Sandbox でも再現しましたか？」をテキスト質問

**再現できない場合の分岐**:

| 状況 | 対応 |
|---|---|
| 別データ・別ユーザ等で再現可能性あり | Phase 1.7 を別シナリオで再試行 |
| 再現条件が investigation.md に欠落 | Phase 1 に戻り再調査 |
| そもそも Backlog と異なる事象 | ユーザに確認のうえ中止 / Phase 1 戻り |

**xlsx 更新**（`{xlsx_folder}` が設定されている場合のみ）:

```bash
python scripts/python/backlog-xlsx/update_records.py \
  --folder "{xlsx_folder}" --issue-id "{issueID}" \
  timeline --phase "再現確認" \
  --content "Sandbox 再現確認: {再現成功/失敗・対象データ}"
```

> **次に進む条件**: 再現成功 + ユーザ確認サインを得た後、「Phase 2 に進んでよろしいですか？」とテキストで確認

---

### Phase 2: 対応方針の確定（backlog-planner Phase A）

> **xlsx 共通規則**: Phase 2 以降の全 xlsx 更新ブロックは `{xlsx_folder}` が null（Phase 1.5 で「作成しない」を選択）の場合スキップする。

`backlog-planner` エージェントを起動する（Phase A: 対応方針）:

```
モード: 対応方針（Phase A）
調査レポート: docs/logs/{issueID}/investigation.md
出力先: docs/logs/{issueID}/approach-plan.md
種別: {issue_type}
default_stance: {バグ="最小修正＋既存への影響ゼロを最優先" / 追加要望="既存類似実装のパターンに合わせる" / その他="案件特性に応じて判断"}
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

> **次に進む条件**: ユーザが対応方針を確認した後 — 成果物サマリーと特に確認したい点をテキストで提示し、やり取りを経て「Phase 3 に進んでよろしいですか？」とテキストで確認する
>
> **特に確認したい点の例**: 「業務要件 Q の回答が方針の前提と合っているか」「推奨案と比較した際の非採用案のリスク許容判断」

---

### Phase 3: 実装方針の確定（backlog-planner Phase B）

`backlog-planner` エージェントを起動する（Phase B: 実装方針）:

```
モード: 実装方針（Phase B）
採用方針: {承認された案名}
調査レポート: docs/logs/{issueID}/investigation.md
出力先: docs/logs/{issueID}/implementation-plan.md
種別: {issue_type}
default_stance: {Phase 2 と同じ値を引き継ぐ}
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

> **次に進む条件**: 全判断ポイントをユーザが確認・確定した後 — 成果物サマリーと特に確認したい点をテキストで提示し、やり取りを経て「Phase 3.5 に進んでよろしいですか？」とテキストで確認する
>
> **特に確認したい点の例**: 「類似実装と異なるパターンを採用した判断ポイントの整合性」「SOQL の LIMIT・権限制御が全ユーザ種別で正しいか」

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

> **次に進む条件**: 全検証項目 OK をユーザが確認した後 — 成果物サマリーと特に確認したい点をテキストで提示し、やり取りを経て「Phase 4 に進んでよろしいですか？ Phase 3 に戻る必要がありますか？」とテキストで確認する
>
> **特に確認したい点の例**: 「新規発見した影響箇所への対処方針」「エビデンスが取れていない項目の扱い」

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

> **次に進む条件**: ユーザが実装内容を確認した後 — 成果物サマリーと特に確認したい点をテキストで提示し、やり取りを経て「Phase 5 に進んでよろしいですか？」とテキストで確認する
>
> **特に確認したい点の例**: 「実装中に発見した計画との不整合の影響評価」「implementation-plan.md への改版履歴追記が必要なら内容の確認」

---

### Phase 5: テスト・検証（backlog-tester）

`backlog-tester` エージェントを起動する:

```
調査レポート: docs/logs/{issueID}/investigation.md
実装計画: docs/logs/{issueID}/implementation-plan.md
種別: {issue_type}
```

テスト結果をユーザに報告する。NG 項目があれば以下の戻り先を判断してから戻る:

| NG の原因 | 戻り先 |
|---|---|
| 実装ミス・コードのバグ | Phase 4（実装修正） |
| 実装方針レベルの判断ミス | Phase 3（実装方針の再確認） |
| 対応方針レベルの設計ミス | Phase 2（対応方針の見直し） |
| 判断できない・複合原因 | ユーザに戻り先をテキストで確認（「Phase 4 / Phase 3 / Phase 2 / 中止 のどれに戻りますか？」と質問） |

戻って修正した後は **全テストケースを再度 Phase 5 で実施**してから Phase 6 に進む（部分的な再テストは不可）。

**xlsx 更新（テスト・検証記録）**（`{xlsx_folder}` が設定されている場合のみ）

```bash
python scripts/python/backlog-xlsx/update_records.py \
  --folder "{xlsx_folder}" --issue-id "{issueID}" \
  timeline --phase "テスト" \
  --content "テスト完了: {PASS/FAIL} / {テスト件数}件実施"
```

> **次に進む条件**: 全テスト PASS かつユーザ確認サインがあった後 — 成果物サマリーと特に確認したい点をテキストで提示し、やり取りを経て「Phase 6 に進んでよろしいですか？」とテキストで確認する
>
> **特に確認したい点の例**: 「ユーザ合同確認が取れていないシナリオの扱い」「Before/After エビデンスが対になっているか」

---

### Phase 6: リリース・お客様確認・完了（backlog-releaser）

`backlog-releaser` エージェントを起動する:

```
実装計画: docs/logs/{issueID}/implementation-plan.md
xlsx_folder: {xlsx_folder}（設定されている場合）
```

**xlsx 更新（リリース）**（`{xlsx_folder}` が設定されている場合のみ）

```bash
python scripts/python/backlog-xlsx/update_records.py \
  --folder "{xlsx_folder}" --issue-id "{issueID}" \
  timeline --phase "リリース" \
  --content "リリース準備完了"
```

**お客様確認サインの取得**

| `{issue_type}` | 取り扱い |
|---|---|
| バグ | **必須**。修正後の再現テスト結果（Phase 5 の 4.5-A エビデンスを含む Before/After 対）を顧客に提示し、確認サインを得る（Backlog コメント返信・メール等）。サイン未取得の状態で完了報告しない |
| 追加要望 | 推奨。UAT 実施予定があれば顧客に確認サインを案内する |
| その他 | 任意 |

**xlsx 更新（お客様確認）**（`{issue_type}` が `バグ` かつ `{xlsx_folder}` が設定されている場合のみ）

```bash
python scripts/python/backlog-xlsx/update_records.py \
  --folder "{xlsx_folder}" --issue-id "{issueID}" \
  timeline --phase "お客様確認" \
  --source "顧客" \
  --content "確認サイン取得: {取得日・確認手段（Backlog コメント / メール等）}"
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
