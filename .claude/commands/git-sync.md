---
description: "プロジェクトGitリポジトリとの同期コマンド。プロジェクト部分（docs/ CLAUDE.md）のpull/pushを実行する。テンプレート更新は /upgrade を使用。"
---

## Step 0: 操作の選択

まず現在のブランチを取得する:
```bash
git rev-parse --abbrev-ref HEAD
```

取得値が `HEAD` の場合は detached HEAD 状態。以下を報告して終了:
```
⚠️ detached HEAD 状態です。ブランチに切り替えてから再実行してください（例: `git checkout main`）
```

AskUserQuestion で操作を選択:

**質問**: 「何をしますか？」

**選択肢**:
- プロジェクト部分を取得する — プロジェクトリポジトリの最新を取得（git pull）
- プロジェクト部分を保存する — 変更したファイルをプロジェクトリポジトリに保存（git push）

> テンプレート（`.claude/` / `scripts/`）の更新は `/upgrade` を使用してください。

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

AskUserQuestion で選択:

**質問**: 「保存するファイルを選択してください」

**選択肢**（multiSelect: false、排他選択）:
- 全て（docs/ + CLAUDE.md）
- docs/ のみ
- CLAUDE.md のみ

### 2. 変更確認

選択したパスに変更があるか確認:

```bash
git status --short {対象パス...}
```

変更が1件もない場合は「保存対象の変更がありません」と報告して終了。

### 3. コミット・push

変更内容からコミットメッセージを自動生成する。形式は以下に固定:

- **prefix**: 変更が `docs/` のみなら `docs:`、`CLAUDE.md` を含む場合は `chore:`
- **suffix**: `git diff --stat` から取得した変更ファイル名を `,` 区切りで列挙（先頭ディレクトリは省略、拡張子は残す）
- 例: `docs: update catalog.md,requirements.md` / `chore: update CLAUDE.md,usecases.md`
- 60 文字を超える場合は `...` で末尾を短縮

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
