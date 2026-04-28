# Phase 1.5: xlsx フォルダパスの確定 — 実行手順

---

## 「作成しない」が選ばれた場合

`{xlsx_folder}` = null として Phase 2 へ進む。

**実装前エビデンスの取得依頼**（「作成しない」場合でも必ず案内する）:
- **バグの場合**: 再現手順を実機で実施し、画面スクリーンショット・コンソールログ・対象レコード値を `docs/logs/{issueID}/evidence/before/` 配下に保存
- **追加要望の場合**: 変更前の現状画面・データの状態をスクリーンショット保存（`docs/logs/{issueID}/evidence/before/` 配下に保存）
- **その他の場合**: 変更前の現状を記録しておくことを推奨する（`docs/logs/{issueID}/evidence/before/` 配下に保存）
- **Playwright が利用可能な場合**: 対象画面のスクリーンショットを自動取得し `docs/logs/{issueID}/evidence/before/auto_{連番}_{説明}.png` に保存

---

## 「作成する」が選ばれた場合

### フォルダパスの確定

`docs/.backlog_config.yml` を確認する（出力が空の場合は初回として扱う）:

```bash
python -c "import yaml,pathlib; p=pathlib.Path('docs/.backlog_config.yml'); d=yaml.safe_load(p.read_text(encoding='utf-8')) if p.exists() else {}; print(d.get('report_dir',''))"
```

- **初回（出力が空）**: 保存先フォルダパスをテキストで入力してもらう（絶対パスで指定。例: `C:/work/backlog_records`）
- **2回目以降（出力に前回パスあり）**: 「{前回のパス}（前回と同じ）か別のパスを指定するか」をテキストで質問する。「別のパスを指定する」の場合は絶対パスでテキスト入力してもらう

確定したパスを `docs/.backlog_config.yml` の `report_dir` に保存する:

```bash
python -c "import yaml,pathlib; pathlib.Path('docs/.backlog_config.yml').write_text(yaml.dump({'report_dir': '{確定したパス}'}), encoding='utf-8')"
```

`{件名}` から Windows 禁則文字を除去した `{件名_sanitized}` を生成する（出力値を変数として保持すること）:

```bash
python -c "import re,sys; print(re.sub(r'[/\\\\:*?\"<>|]', '_', sys.argv[1]))" "{件名}"
```

`{xlsx_folder}` = `{report_dir}/{issueID}_{件名_sanitized}` として会話の最後まで保持する。

**xlsx ファイルの生成は Phase 3 末尾（実装方針確定後）で実施する。この時点では生成しない。**

### 実装前エビデンスの取得依頼

ユーザに以下を案内する:
- **バグの場合**: 再現手順を実機で実施し、画面スクリーンショット・コンソールログ・対象レコード値を取得し `docs/logs/{issueID}/evidence/before/` 配下に保存（Phase 3 末尾生成後は `{xlsx_folder}/{issueID}_エビデンス.xlsx` の「実装前エビデンス」欄にも貼付）
- **追加要望の場合**: 変更前の現状画面・データの状態をスクリーンショット保存（変更後との比較用）。`docs/logs/{issueID}/evidence/before/` 配下に保存
- **その他の場合**: 変更前の現状を記録しておくことを推奨する（`docs/logs/{issueID}/evidence/before/` 配下に保存）
- **Playwright が利用可能な場合**: 対象画面のスクリーンショットを自動取得し `docs/logs/{issueID}/evidence/before/auto_{連番}_{説明}.png` に保存

エビデンスは Phase 3.5（実装前検証）と Phase 5（クロステスト）で参照される。

---

## 次に進む条件

フォルダパス確定・エビデンス取得依頼の後 — デプロイ適否判定セクション（backlog.md 末尾）を参照し、「Phase 2 に進んでよろしいですか？」とテキストで確認する。
