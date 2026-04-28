# Phase 1.5: 対応記録ファイルの作成 — 実行手順

AskUserQuestion の選択結果に応じて以下のいずれかを実行する。

---

## 「作成しない」が選ばれた場合

`{xlsx_folder}` = null として Phase 2 へ進む。途中で xlsx を追加したくなった場合は「Phase 1.5 をもう一度実行する」とユーザに伝えればよい。

**実装前エビデンスの取得依頼**（「作成しない」場合でも必ず案内する）:
- **バグの場合**: 再現手順を実機で実施し、画面スクリーンショット・コンソールログ・対象レコード値を取得し `docs/logs/{issueID}/evidence/before/` 配下に保存
- **追加要望の場合**: 変更前の現状画面・データの状態をスクリーンショット保存（変更後との比較用）。`docs/logs/{issueID}/evidence/before/` 配下に保存
- **その他の場合**: 変更前の現状（対象画面・データ・処理結果等）を記録しておくことを推奨する（スクリーンショットまたはファイルで `docs/logs/{issueID}/evidence/before/` 配下に保存）
- **Playwright が利用可能な場合**（`.mcp.json` に playwright MCP サーバー設定があり、対象画面が Sandbox 認証済みブラウザで開ける場合）: エージェント側でも対象画面のスクリーンショットを自動取得し `docs/logs/{issueID}/evidence/before/auto_{連番}_{説明}.png` に保存する（精度が低い場合はユーザ案内のみ）

---

## 「作成する」が選ばれた場合

### フォルダパスの確定

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

### xlsx の生成

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
- ユーザーに失敗内容を報告し、「エクセルなしで続行 / 中止 のどちらにしますか？」とテキストで質問する
- 「エクセルなしで続行」が選ばれた場合: `{xlsx_folder}` を null に設定して Phase 2 へ進む

### xlsx 更新（調査・影響範囲）

```bash
python scripts/python/backlog-xlsx/update_records.py \
  --folder "{xlsx_folder}" --issue-id "{issueID}" \
  timeline --phase "調査" \
  --content "調査完了: {根本原因または要件の本質を1行で}"
```

### 実装前エビデンスの取得依頼

ユーザに以下を案内する:
- **バグの場合**: 再現手順を実機で実施し、画面スクリーンショット・コンソールログ・対象レコード値を取得。`{xlsx_folder}/{issueID}_対応記録.xlsx` のエビデンスシート「実装前エビデンス」欄に貼付、または `docs/logs/{issueID}/evidence/before/` 配下に保存
- **追加要望の場合**: 変更前の現状画面・データの状態をスクリーンショット保存（変更後との比較用）。エビデンスシートまたは `docs/logs/{issueID}/evidence/before/` 配下に保存
- **その他の場合**: 変更前の現状を記録しておくことを推奨する（エビデンスシートまたは `docs/logs/{issueID}/evidence/before/` 配下に保存）
- **Playwright が利用可能な場合**: エージェント側でも対象画面のスクリーンショットを自動取得し `docs/logs/{issueID}/evidence/before/auto_{連番}_{説明}.png` に保存する（精度が低い場合はユーザ案内のみ）

エビデンスは Phase 3.5（実装前検証）と Phase 5（クロステスト）で参照される。

---

## 次に進む条件

xlsx 生成・エビデンス取得・調査レポートをユーザが確認した後 — デプロイ適否判定セクション（backlog.md 末尾）を参照し、「Phase 2 に進んでよろしいですか？」とテキストで確認する。
