---
description: "プロジェクトGitリポジトリとの同期コマンド。テンプレート部分（.claude/ scripts/）の更新、またはプロジェクト部分（docs/ CLAUDE.md force-app/）のpull/pushを実行する。"
---

## Step 0: 操作の選択

まず現在のブランチを取得する:
```bash
git rev-parse --abbrev-ref HEAD
```

AskUserQuestion で操作を選択:

**質問**: 「何をしますか？」

**選択肢**:
- テンプレート部分を更新する — .claude/ scripts/ を最新テンプレートから反映してプロジェクトリポジトリにも保存
- プロジェクト部分を取得する — プロジェクトリポジトリの最新を取得（git pull）
- プロジェクト部分を保存する — 変更したファイルをプロジェクトリポジトリに保存（git push）

---

## テンプレート部分を更新する

### 1. upgrade 実行

```bash
bash scripts/upgrade.sh
```

失敗した場合はエラー内容を報告して終了。

### 2. プロジェクトリポジトリへ push

upgrade の完了メッセージに "コミット完了" が含まれる場合（変更があった場合）のみ push する:

```bash
git push origin HEAD
```

変更がなかった場合（"テンプレートは最新です" の場合）は push せずに報告:
```
✅ テンプレートは既に最新です。push は不要です。
```

変更があった場合:
```
✅ テンプレート更新 + push 完了
```

---

## プロジェクト部分を取得する

```bash
git pull origin {Step 0 で取得したブランチ名}
```

完了後、更新されたファイル一覧を表示して報告:
```
✅ 取得完了 — {更新ファイル数}件のファイルが更新されました
```

変更がなかった場合:
```
✅ 既に最新です。
```

---

## プロジェクト部分を保存する

### 1. 対象ファイルの選択

AskUserQuestion で選択（複数選択可）:

**質問**: 「保存するファイルを選択してください」

**選択肢**（multiSelect: true）:
- 全て（docs/ + CLAUDE.md + force-app/）
- docs/ のみ
- CLAUDE.md のみ
- force-app/ のみ

「全て」が選択された場合は残りの選択肢を無視して `docs/ CLAUDE.md force-app/` を対象とする。

### 2. 変更確認

選択したパスに変更があるか確認:

```bash
git status --short {対象パス...}
```

変更が1件もない場合は「保存対象の変更がありません」と報告して終了。

### 3. コミット・push

変更内容（git diff --stat の結果）からコミットメッセージを自動生成する。形式: `{主な変更内容を1行で}` （例: `docs: update catalog`, `chore: update requirements and usecases`）

```bash
git add {対象パス...}
git commit -m "{自動生成したコミットメッセージ}"
git push origin HEAD
```

完了報告:
```
✅ 保存完了 — {コミットメッセージ}
```

エラーが発生した場合（リモート未設定等）はエラー内容を報告して終了。
